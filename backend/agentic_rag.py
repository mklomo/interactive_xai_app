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
    """
    Take a text path and generate a texts list
    """
    with open(text_path, "r") as file:   # ← use the passed argument
        text = file.read().replace("\n", "")
    texts = text.split("--")
    return texts






def text_splitter_search(user_query: str) -> list[dict]:
    """
    Performs semantic search using Cohere embeddings and FAISS index.
    """
    try:
        texts = generate_texts(TEXT_PATH)
        text_split_index = faiss.read_index(TEXT_SPLITTER_INDEX_PATH)

        # texts first in the call sometimes helps older SDK versions
        embed_response = CO.embed(
            texts=[user_query],
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"],
        )

        query_embed = embed_response.embeddings.float_[0]

        query_embed_np = np.array([query_embed], dtype=np.float32)
        distances, similar_item_ids = text_split_index.search(query_embed_np, NUMBER_OF_RESULTS)

        texts_np = np.array(texts)
        results = pd.DataFrame({
            'texts': texts_np[similar_item_ids[0]],
            'distance': distances[0]
        })

        return [{'text': text} for text in results['texts']]

    except FileNotFoundError as e:
        raise ValueError(f"Missing file: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error in text_splitter_search: {str(e)}") from e

        



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
            # "review_text": review_df["review_text"],
            # "feature_values": review_df[features],
            # "ebm_model_pred": review_df["ebm_prediction"],
            # "ebm_model_pred_confidence": review_df["model_pred_confidence"],
            "feature_importance_contributions": feature_imp_scores,
            "Search Docs Context": docs_dict,
        }
    ]
    return model_context


# Tool Schemas for Cohere Command R+ (updated to match new context)
tools = [
    # Tool 1
    {
        "type": "function",
        "function": {
            "name": "get_prediction_context",
            "description": "gets the context of the prediction, i.e., review_text, feature_values, ebm_model_pred, ebm_model_pred_confidence and feature_importance_contributions",
            "parameters": {
                "type": "object",
                "properties": {
                    "review_df": {
                        "type": "object",
                        "description": "A Pandas DataFrame object containing review data with necessary columns for prediction context extraction."
                    },
                        "user_query": {
                            "type": "string",
                            "description": "The user query used to retrieve relevant search documents via semantic search."
                    }
                },
                "required": ["review_df", "user_query"]
            },
        },
    },
    # Tool 2
    {
        "type": "function",
        "function": {
            "name": "text_splitter_search",
            "description": "Performs a semantic search on a pre-indexed collection of text splits using Cohere embeddings and FAISS. It embeds the user query, searches the FAISS index for nearest neighbors, and returns a list of dictionaries with the most similar text snippets. Uses Cohere's 'embed-english-v3.0' model for English queries",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "The user query string to embed and match against the indexed texts."
                    }
                },
                "required": ["user_query"]
            },
        },
    },
]



def run_agent(user_query, review_df, model="command-a-03-2025"):
    # Step 1: Get the user message
    messages = [
            {
                # System
                "role": "system",
                # System Instruction
                "content": """
Role: You are an Explainable AI assistant, acting as a patient tutor for undergraduate students learning about AI.

CRITICAL RULE (always follow first):
If the user's query is off-topic, gibberish, nonsense, unrelated to the specific review, its text, its words, its features, or the model's prediction on that review, respond with EXACTLY this sentence and nothing else:

"The Review Agent cannot respond to queries outside the review."

Do not explain, do not be helpful, do not try to interpret the gibberish — just return that exact message.

Only when the query is clearly about the review or the model's prediction on it are you allowed to use tools and answer normally.


Purpose: Your goal is to help students understand why an AI model, called the Review Agent, made a specific prediction on a review, by reasoning through the available data and providing simple, clear rationales that connect the dots without just listing facts.

Method:
Always start by gathering context using the available tools: Use get_prediction_context to retrieve feature importances (which users see as a graph or chart) for questions about importances or visuals. Use text_splitter_search to find specific evidence from the review text for explanations tied to features or content. For questions about the content, text, or words of the review, reason deliberately step-by-step and connect any specific response to find specific evidence from the review text/words for explanations.

Deliberatively reason step-by-step: Analyze the tool results in the context of the query, explain how the data leads to the model's decision (e.g., "This feature matters because..."), and tie it back to the review's prediction. Note that you have access to the text or content of the review and reason deliberately about this.
For questions about the content of the review, specifically about words influencing the predictions, reason step-by-step about the review text (you have access to it), using text_splitter_search to identify specific evidence from the words or text in the review tied to the features and the model's prediction to generate explanations.

Score Interpretation (Very Important – matches the EBM model and Explanation Visualization chart):
- Positive feature importance scores increase the likelihood of the review being **Genuine** (bars extending right on the chart).
- Negative feature importance scores increase the likelihood of the review being **Deceptive** (bars extending left on the chart).
- The larger the absolute value, the stronger that feature’s push toward the prediction.

Remap technical feature names for clarity using this dictionary:
remap_dict = {
    "proportion_of_emotional_content_in_review": "Emotional Content in the Review",
    "proportion_of_adjectives_in_review": "Proportion of Adjectives in the Review",
    "readability_of_review": "Readability of the Review",
    "analytic_writing_style": "Analytic Writing Style of the Review",
}

For off-topic questions not about the review or the content or text of the review, or the model's predictions, respond only with: "The Review Agent cannot respond to queries outside the review."

Structure responses as 3-5 sentences or bullet points, focusing on rationale over raw data.
Personality: Approachable and encouraging, like a helpful classmate who breaks down complex ideas simply.
Tone: Clear, concise, and everyday – avoid jargon (explain if needed, e.g., "feature importance is like how much weight a certain word carries in the AI's choice"), and emphasize logical reasoning to build understanding.
"""
            },
            # User content
            {
                "role": "user", 
                # User Query
                "content": user_query
            },
        ]
    # CRITICAL: Inject the review DataFrame so the model knows what it's explaining
    messages[1]["content"] += f"\nReview DataFrame: {review_df.to_dict(orient='records')}"
    chat_params = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.7
    }

    try:
        response = CO.chat(**chat_params)
    except Exception as e:
        return f"API Error: {str(e)}"
     
    # Step 2: Handle Tool Calls
    while response.message.tool_calls:
        # Add the assistant's tool call plan to history
        messages.append({
            "role": "assistant", 
            "tool_calls": response.message.tool_calls,
            "tool_plan": response.message.tool_plan,    
        })

        # Process each tool call in this turn
        for tool_call in response.message.tool_calls:
            raw_args = tool_call.function.arguments
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args if isinstance(raw_args, dict) else {}
            result_str = ""

            if tool_call.function.name == "text_splitter_search":
                tool_query = args.get("user_query", "")
                if not tool_query.strip():
                    tool_results = [{"text": "No specific context found for empty query."}]
                else:
                    tool_results = text_splitter_search(tool_query)
                result_str = json.dumps(tool_results)
                
            elif tool_call.function.name == "get_prediction_context":
                # Use a unique name for the query search string
                ctx_query = args.get("user_query") or user_query                 
                tool_results = get_prediction_context(review_df=review_df, 
                                                      user_query=ctx_query)
                result_str = json.dumps(tool_results)
            
            # Append the specific tool response to history
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": [{"type": "text", "text": result_str}]
            })

        # Step 3: Get the next response (either more tools or the final answer)
        response = CO.chat(
            model=model, 
            messages=messages, 
            tools=tools, 
            temperature=0.7
        )
    
    # Step 4: Final Assistant Response
    final_text = response.message.content[0].text
    messages.append({"role": "assistant", "content": final_text})
    
    return messages


