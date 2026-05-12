import os
import cohere
import faiss
import numpy as np
import pickle
import pandas as pd
from backend.static_exp import get_static_explanation_data
import json
import streamlit as st


COHERE_API_KEY = st.secrets["api_keys"]["cohere_api_key"]
CO = cohere.ClientV2(api_key=COHERE_API_KEY)  # Updated to ClientV2 as per new chunking code
NUMBER_OF_RESULTS = 2
# Model
MODEL = "command-a-03-2025"
# Paths (adjust as needed)
TEXT_SPLITTER_INDEX_PATH = "backend/data/agentic_rag/text_splitter_chunks.faiss"
TEXT_PATH = "backend/data/linguistic_cues_context.txt"




def generate_texts(text_path):
    with open(text_path, "r") as file:
        text = file.read().replace("\n", "")
    return text.split("--")

# Global variables (RAM is faster than Disk)
TEXTS_CACHE = generate_texts(TEXT_PATH)
FAISS_INDEX_CACHE = faiss.read_index(TEXT_SPLITTER_INDEX_PATH)
TEXTS_NP_CACHE = np.array(TEXTS_CACHE)



def text_splitter_search(user_query: str) -> list[dict]:
    """
    Performs semantic search using Cohere embeddings and FAISS index.
    """
    # Check if the query is empty or just whitespace
    if not user_query or not user_query.strip():
        return [{"text": "No search query provided."}]
        
    # texts first in the call sometimes helps older SDK versions
    embed_response = CO.embed(
            texts=[user_query],
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"],
        )

    query_embed = embed_response.embeddings.float_[0]

    query_embed_np = np.array([query_embed], dtype=np.float32)
    distances, similar_item_ids = FAISS_INDEX_CACHE.search(query_embed_np, NUMBER_OF_RESULTS)

    results = pd.DataFrame({
            'texts': TEXTS_NP_CACHE[similar_item_ids[0]],
            'distance': distances[0]
        })

    return [{'text': text} for text in results['texts']]

        



def get_prediction_context(review_df: pd.DataFrame, 
                           user_query: str):
    """
    Generates prediction context for a review, including explanations from search.
    
    Args:
        review_df (pd.DataFrame): DataFrame with review data (expects single row).
        user_query (str): Query for explanation search.
    
    Returns:
        dict: Context with review details, predictions, and explanations.
    """
    # Tool Definition (integrated from provided snippet)
    features = ["proportion_of_emotional_content_in_review", 
                "proportion_of_adjectives_in_review", 
                "readability_of_review", 
                "analytic_writing_style"]
    feature_imp_scores = get_static_explanation_data(df=review_df)  
    docs_dict = text_splitter_search(user_query)
    model_context = [
        {
            "feature_importance_contributions": feature_imp_scores,
            "Search Docs Context": docs_dict,
        }
    ]
    return model_context


# Tool Schemas for Cohere Command R+ (updated to match new context)
# tools = [
#     # Tool 1
#     {
#         "type": "function",
#         "function": {
#             "name": "get_prediction_context",
#             "description": "gets the context of the prediction, i.e., review_text, feature_values, ebm_model_pred, ebm_model_pred_confidence and feature_importance_contributions",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "review_df": {
#                         "type": "object",
#                         "description": "A Pandas DataFrame object containing review data with necessary columns for prediction context extraction."
#                     },
#                         "user_query": {
#                             "type": "string",
#                             "description": "The user query used to retrieve relevant search documents via semantic search."
#                     }
#                 },
#                 "required": ["review_df", "user_query"]
#             },
#         },
#     },
    # # Tool 2
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "text_splitter_search",
    #         "description": "Performs a semantic search on a pre-indexed collection of text splits using Cohere embeddings and FAISS. It embeds the user query, searches the FAISS index for nearest neighbors, and returns a list of dictionaries with the most similar text snippets. Uses Cohere's 'embed-english-v3.0' model for English queries",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "user_query": {
    #                     "type": "string",
    #                     "description": "The user query string to embed and match against the indexed texts."
    #                 }
    #             },
    #             "required": ["user_query"]
    #         },
    #     },
    # },
# ]



def run_agent(user_query, review_df, model="command-a-03-2025"):
    try:
        # Get semantic search results (only once)
        docs_dict = text_splitter_search(user_query)

        # Safely prepare context
        context_data_df = review_df.drop(columns=["review_id", "stage"], errors="ignore").iloc[0]

        context_data = {
            "review_text": str(context_data_df["review_text"]),
            "feature_importance_scores": {
                "proportion_of_emotional_content_in_review": float(context_data_df["proportion_of_emotional_content_in_review"]),
                "proportion_of_adjectives_in_review": float(context_data_df["proportion_of_adjectives_in_review"]),
                "readability_of_review": float(context_data_df["readability_of_review"]),
                "analytic_writing_style": float(context_data_df["analytic_writing_style"])
            },
            "ebm_prediction": str(context_data_df.get("ebm_prediction", "")),
            "additional_context_for_reasoning": docs_dict   # fixed typo
        }
    except Exception as e:
        raise RuntimeError(f"Context Gathering Failed: {str(e)}")

    # Build messages
    messages = [
        {
            "role": "system",
            "content": """
You are the Review Agent — an Explainable AI assistant.

CRITICAL RULE (always follow first):
If the user's query is off-topic, gibberish, nonsense, or unrelated to the specific review, its text, its words, its features, or the model's prediction on that review, respond with EXACTLY this sentence and nothing else:

"The Review Agent cannot respond to queries outside the review."

Only when the query is clearly about the review or the model's prediction are you allowed to answer normally.

You already have ALL the information you need in the user message:
• review_text
• feature_importance_scores (a dictionary with the four features)
• ebm_prediction
• additional_context_for_reasoning (semantic search results from the review text)

Method:
1. Read the provided context carefully.
2. Think step-by-step about how the feature importance scores and the review text support the prediction.
3. Explain the reasoning in plain language.
4. Connect specific words or patterns from the review text to the features when possible.

Score Interpretation (Very Important):
- Positive feature importance scores push the prediction toward **Genuine** (bars going right on the chart).
- Negative feature importance scores push the prediction toward **Deceptive** (bars going left on the chart).
- Larger absolute values = stronger influence.

Use this mapping to make feature names student-friendly:
"proportion_of_emotional_content_in_review" → "Emotional Content in the Review"
"proportion_of_adjectives_in_review" → "Proportion of Adjectives in the Review"
"readability_of_review" → "Readability of the Review"
"analytic_writing_style" → "Analytic Writing Style of the Review"

Response Style:
• Keep responses to 3–5 sentences or bullet points.
• Focus on clear rationale and logical connections rather than raw numbers.
• Be approachable and encouraging, like a helpful classmate.
• Use everyday language — avoid jargon (or briefly explain it if needed).

Your job is to build the student's understanding of how the AI made its decision.
"""
        },
        {
            "role": "user",
            "content": f"Query: {user_query}\n\nHere is the data you need for analysis:\n{json.dumps(context_data)}"
        },
    ]

    try:
        response = CO.chat(
            model=model,
            messages=messages,
            temperature=0.7
        )
        final_text = response.message.content[0].text
        messages.append({"role": "assistant", "content": final_text})
        return messages
    except Exception as e:
        # Also return a proper list on API errors
        error_msg = f"API Error: {str(e)}"
        raise RuntimeError(f"Cohere API Failed: {str(e)}")  

