"""
Audio Query Processor - Evaluation Module

This module contains evaluation functionality for the Audio Query Processor.
It defines a model for evaluating query accuracy and runs evaluations on a test dataset.

Author: Prateek Chhikara
"""

import asyncio
import weave
import json
import numpy as np
from utils import generate_response
from prompts import COLUMN_SELECTION_PROMPT, QUERY_PROMPT
from weave import Model

# Initialize Weave with project name
weave.init('audio_query_data')

@weave.op()
def get_fields_description():
    """
    Get the description of database fields from the columns.json file.
    
    Returns:
        dict: A dictionary containing column names and their descriptions
    """
    with open("columns.json", "r") as f:
        columns_with_description = json.load(f)
    return columns_with_description

# Test queries for evaluation
user_queries = [
    "models which has latency less than 100ms",
    "models which has accuracy greater than 90%",
    "models which has F1 score greater than 0.95"
]

# Ground truth filters for each test query
gt_filters = [
    {
        "$expr": {
            "$lt": [
                {"$convert": {"input": {"$getField": "output.model_latency.mean"}, "to": "double"}},
                {"$literal": 100}
            ]
        }
    },
    {
        "$expr": {
            "$gt": [
                {"$convert": {"input": {"$getField": "output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy"}, "to": "double"}},
                {"$literal": 0.9}
            ]
        }
    },
    {
        "$expr": {
            "$gt": [
                {"$convert": {"input": {"$getField": "output.HalluScorerEvaluator.scorer_evaluation_metrics.F1"}, "to": "double"}},
                {"$literal": 0.95}
            ]
        }
    }
]

# Combine queries and ground truth filters into an evaluation dataset
eval_dataset = [
    {'id': '0', 'user_query': user_queries[0], 'gt_filters': gt_filters[0]},
    {'id': '1', 'user_query': user_queries[1], 'gt_filters': gt_filters[1]},
    {'id': '2', 'user_query': user_queries[2], 'gt_filters': gt_filters[2]}
]

class QueryEvalModel(Model):
    """
    Model for evaluating query generation accuracy.
    
    This model takes a user query as input and generates a database query
    using the same pipeline as the main application.
    """
    
    @weave.op()
    def predict(self, user_query: str) -> dict:
        """
        Generate a database query from a user query.
        
        Args:
            user_query (str): The natural language query from the user
            
        Returns:
            dict: A dictionary containing the generated database query
        """
        # First, identify required columns based on the query
        query = generate_response(
            user_query, 
            get_fields_description(), 
            "", 
            COLUMN_SELECTION_PROMPT
        )["columns"]
        
        # Then, generate the final query using the identified columns
        query = generate_response(
            user_query, 
            get_fields_description(), 
            query, 
            QUERY_PROMPT
        )["query"]
        
        return {"query": query}

@weave.op()
async def query_accuracy_score(user_query, output):
    """
    Calculate the accuracy score for a generated query.
    
    This function compares the generated query with an expected query
    generated using the same pipeline.
    
    Args:
        user_query (str): The natural language query from the user
        output (dict): The output from the QueryEvalModel
        
    Returns:
        dict: A dictionary containing the accuracy score (1 for match, 0 for mismatch)
    """
    # Generate the expected query using the same pipeline
    expected_query = generate_response(
        user_query, 
        get_fields_description(), 
        "", 
        COLUMN_SELECTION_PROMPT
    )["columns"]
    
    expected_query = generate_response(
        user_query, 
        get_fields_description(), 
        expected_query, 
        QUERY_PROMPT
    )["query"]
    
    # Compare the generated query with the expected query
    score = 1 if expected_query == output["query"] else 0
    return {"accuracy": score}

# Initialize the evaluation model
model = QueryEvalModel()

# Create an evaluation with the test dataset
evaluation = weave.Evaluation(
    dataset=[{"user_query": eval["user_query"]} for eval in eval_dataset], 
    scorers=[query_accuracy_score]
)

# Run the evaluation
if __name__ == "__main__":
    asyncio.run(evaluation.evaluate(model))
    print("Evaluation completed successfully!")
