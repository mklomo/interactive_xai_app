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
        Take a text path and generate a texts lists
        input:
            text_path = file path
        output:
            texts = texts in a list format
    """
    with open(TEXT_PATH, "r") as file:
        # Remove all newline characters
        text = file.read().replace("\n", "")
    texts = text.split("--")
    return texts






# Standalone helper function for text splitter search
def text_splitter_search(user_query: str) -> list[dict]:
    """
    Performs semantic search using Cohere embeddings and FAISS index.
    
    Args:
        user_query (str): The search query.
    
    Returns:
        list[dict]: List of dicts with 'text' keys for matching documents.
    """
    try:
        # Load texts from pickle (as per refactor comment)
        texts = generate_texts(TEXT_PATH)
        
        # Load FAISS index
        text_split_index = faiss.read_index(TEXT_SPLITTER_INDEX_PATH)
        
        # Get query embedding
        # print
        # print(f"Query --> {user_query}")
        query_embed = CO.embed(
            texts=[user_query],
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"]
        ).embeddings.float[0]
        
        # Retrieve nearest neighbors
        query_embed_np = np.array([query_embed], dtype=np.float32)
        distances, similar_item_ids = text_split_index.search(query_embed_np, NUMBER_OF_RESULTS)
        
        # Format results
        texts_np = np.array(texts)
        results = pd.DataFrame({
            'texts': texts_np[similar_item_ids[0]],
            'distance': distances[0]
        })
        
        results_dict_list = [{'text': text} for text in results['texts']]
        return results_dict_list
    
    except FileNotFoundError as e:
        raise ValueError(f"Missing file: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error in text_splitter_search: {str(e)}")



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
Role: You are an XAI assistant, acting as a patient tutor for undergraduate students learning about AI.
Purpose: Your goal is to help students understand why an AI model made a specific prediction on a review, by reasoning through the available data and providing simple, clear rationales that connect the dots without just listing facts.

Method:
Always start by gathering context using the available tools: Use get_prediction_context to retrieve feature importances (which users see as a graph or chart) for questions about importances or visuals. Use text_splitter_search to find specific evidence from the review text for explanations tied to features or content.

Deliberatively reason step-by-step: Analyze the tool results in the context of the query, explain how the data leads to the model's decision (e.g., "This feature matters because..."), and tie it back to the review's prediction. 

For questions about the content of the review, e.g., words influencing the predictions, deliberatively reason step-by-step about the content of the review (you have access to this), using text_splitter_search to understand specific evidence from the review text for tied to Interpretations.

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

For off-topic questions not about the review, its content, or the model's predictions, respond only with: "The Review Agent cannot respond to queries outside the review."

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
    
    # iteration = 0
    
    first_call = True
    
    # Step 2: Generate tool calls (if any)
    # Chat Params based on user message
    chat_params = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.7
        }
    if first_call:
        # Update User Content with the review DataFrame
        messages[1]["content"] += f"\nReview DataFrame: {review_df.to_dict(orient='records')}"
        # chat_params["tool_choice"] = "REQUIRED"  # Force tool use; valid for Cohere
        first_call = False
    try:
        # Generate response without tools
        response = CO.chat(**chat_params)
    except Exception as e:
        return f"API Error: {str(e)}"
     
    while response.message.tool_calls:
        # print("TOOL PLAN:")
        # print(response.message.tool_plan, "\n")
        # print("TOOL CALLS:")
        # Assistant for tool calls
        messages.append({
            "role": "assistant", 
            # "content": response.message.content[0].text, 
            "tool_calls": response.message.tool_calls,
            "tool_plan": response.message.tool_plan,    
            })
        tool_content = []
        for tool_call in response.message.tool_calls:
            # If running a semantic search
            if tool_call.function.name == "text_splitter_search":
                #print(f"Tool Name: {tool_call.function.name}")
                # Get the query
                user_query = json.loads(tool_call.function.arguments)["user_query"]
                #print(f"Text Splitter Query --> {user_query}")
                # Get the reasults from the tool call
                tool_results = text_splitter_search(user_query)
                #print(f"Text Splitter TOOL RES--> {tool_results}")
                # Append results
                tool_content.append(json.dumps(tool_results))
                # Append the tool output to the messages
                messages.append({
                    "role": "tool", 
                    "tool_call_id": tool_call.id, 
                    "content": tool_content
                })

            # elif running a prediction_context
            elif tool_call.function.name == "get_prediction_context":
                # Get the df
                #print(f"\n ARGS -->{tool_call.function.arguments} \n")
                review_df_dict = json.loads(tool_call.function.arguments)["review_df"][0]
                try:
                    query_str = json.loads(tool_call.function.arguments)["user_query"] 
                except:
                    query_str = user_query
                # Convert to a DF
                #print(f" Review DF Dict{review_df_dict}")
                #print(f"\nQuery --> {query_str}")
                review_df = pd.DataFrame([review_df_dict])
                # print(f" Review DF -> {review_df}")
                # Get results from the prediction context
                tool_results = get_prediction_context(review_df=review_df, user_query=query_str)
                #print(f" Tool Results --> {tool_results}")
                # Append results
                tool_content.append(str(tool_results))
                # Append the tool output to the messages
                messages.append({
                    "role": "tool", 
                    "tool_call_id": tool_call.id, 
                    "content": tool_content
                })
        
            
        # Step 4: Generate response
        response = CO.chat(model=model, 
                           messages=messages, 
                           tools=tools, 
                           temperature=0.7)
    
    messages.append({"role": "assistant", "content": response.message.content[0].text})
    # Print final response
    # print("Response:")
    # print(response.message.content[0].text)
    # print("=" * 50)
    # print(f"\nMessages --> {messages}")
    return messages


