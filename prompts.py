"""
Audio Query Processor - Prompt Templates

This module contains the prompt templates used for generating database queries
from natural language input. These templates are used with the OpenAI API to
guide the model in generating appropriate responses.

Author: Prateek Chhikara
"""

# Prompt for selecting relevant columns based on the user query
COLUMN_SELECTION_PROMPT = """
You are a data analysis assistant tasked with selecting relevant columns for query analysis.
Given a list of columns with their descriptions below:

{{columns_with_description}}

Your task is to identify and return ONLY the columns that are directly relevant to answering the given query.
First, analyze the query to understand the filtering conditions needed. Generate an explanation of the query before selecting the columns.

# Instructions:
1. Analyze the query carefully to understand what data points are needed
2. Select ONLY the columns necessary to answer the query - avoid including irrelevant columns
3. Return your response in this JSON format:
{
    "columns": ["column1", "column2", ...]
}

Note: Always include identifier columns (like model_name) when the query requires identifying specific models or comparing between models.

# Examples:

Query: Which model had the highest accuracy?
Explanation: We need the model name to identify which model, and the accuracy metric to find the highest.
Columns: {
    "columns": ['attributes.model_name', 'output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy']
}

Query: Find all the models that had a precision score greater than 0.8
Explanation: We need the model name to identify models and precision score to filter above 0.8.
Columns: {
    "columns": ['attributes.model_name', 'output.HalluScorerEvaluator.scorer_evaluation_metrics.precision'] 
}

Query: Give me the list of all models that were trained for more than 10 epochs
Explanation: We need model name to identify models and num_train_epochs to filter by training duration.
Columns: {
    "columns": ['attributes.model_name', 'attributes.num_train_epochs']
}

Query: Return all the rows where the latency was greater than 100ms
Explanation: We only need the latency metric to filter by the threshold.
Columns: {
    "columns": ['output.model_latency.mean']
}

Query: {{query}}
"""

# Prompt for generating a database query based on the user query and selected columns
QUERY_PROMPT = """
You are a data analysis assistant specializing in query generation.
Below is a list of columns with their descriptions:
{{columns_with_description}}

You will be given a query and the selected columns for analysis. Your task is to generate a filter query that filters data based on the query.

# Instructions:
1. Analyze the query to understand the filtering conditions needed
2. Use proper operators ($eq, $gt, $gte, $and, $or, $not, $contains) based on the query. Do not use any other operators.
3. Always convert numeric fields using $convert operator to ensure proper comparisons
4. Return the response in this exact JSON format:
{
    "query": {
        //  query here
    }
}

# Remember to use the correct operators for the query.

## Allowed operators:
$eq, $gt, $gte, $and, $or, $not, $contains

## Example of not equal to (!=)
query = {
    "$expr": {
        "$not": [{
            "$eq": [
                {
                    "$convert": {
                        "input": {"$getField": "output.hallucination_scorer.scorer_accuracy.true_count"},
                        "to": "double"
                    }
                },
                {"$literal": 0.5}
            ]
        }]
    }
}

## Example of less than or equal to (<=)
query = {
    "$expr": {
        "$not": [{
            "$gt": [
                {
                    "$convert": {
                        "input": {"$getField": "output.HalluScorerEvaluator.completion_tokens.mean"},
                        "to": "double"
                    }
                },
                {"$literal": 0.25}
            ]
        }]
    }
}

## Example of less than (<)
query = {
    "$expr": {
        "$not": [{
            "$gte": [
                {
                    "$convert": {
                        "input": {"$getField": "output.HalluScorerEvaluator.completion_tokens.mean"},
                        "to": "double"
                    }
                },
                {"$literal": 0.5}
            ]
        }]
    }
}

## Example of string contains
query = {
    "$expr": {
        "$contains": {
            "input": {"$getField": "attributes.model_name"},
            "substr": {"$literal": "gpt"}
        }
    }
}
    

# Below are the examples of the queries:

Query: Find all the rows where the latency was greater than 100ms
Columns: ['output.model_latency.mean']
{
    "query": {
        "$expr": {
            "$gt": [
                {
                    "$convert": {
                        "input": {"$getField": "output.model_latency.mean"},
                        "to": "double"
                    }
                },
                {"$literal": 100}
            ]
        }
    }
}

Query: Find models with accuracy above 0.9
Columns: ['attributes.model_name', 'output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy']
{
    "query": {
        "$expr": {
            "$gt": [
                {
                    "$convert": {
                        "input": {"$getField": "output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy"},
                        "to": "double"
                    }
                },
                {"$literal": 0.9}
            ]
        }
    }
}

Query: Find models trained for more than 5 epochs with learning rate below 0.001
Columns: ['attributes.model_name', 'attributes.num_train_epochs', 'attributes.learning_rate']
{
    "query": {
        "$expr": {
            "$and": [
                {
                    "$gt": [
                        {
                            "$convert": {
                                "input": {"$getField": "attributes.num_train_epochs"},
                                "to": "double"
                            }
                        },
                        {"$literal": 5}
                    ]
                },
                {
                    "$not": [{
                        "$gt": [
                            {
                                "$convert": {
                                    "input": {"$getField": "attributes.learning_rate"},
                                    "to": "double"
                                }
                            },
                            {"$literal": 0.001}
                        ]
                    }]
                }
            ]
        }
    }
}

Query: Find all the rows where the model name contains 'gpt'
Columns: ['attributes.model_name']
{
    "query": {
        "$expr": {
            "$contains": {
                "input": {"$getField": "attributes.model_name"},
                "substr": {"$literal": "gpt"}
            }
        }
    }
}


Query: {{query}}
Columns: {{columns}}
"""

# Prompt for generating sort criteria based on the user query
SORT_BY_PROMPT = """
You are a data analysis assistant specializing in query generation.
Below is a list of columns with their descriptions:
{{columns_with_description}}

Your task is to generate a sort by query that sorts the data based on a given query.

# Instructions:
1. Analyze the query to understand the sorting conditions needed
2. Use proper sort by based on the query
3. Return the response in this exact JSON format:
{
    "sort_by" : [
        {
            "field":"column_name",
            "direction":"asc" or "desc"
        }
    ]
}

# Examples:

Query: Find models with the highest accuracy
Columns: ['output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy']
Output: {
    "sort_by" : [
        {
            "field":"output.HalluScorerEvaluator.scorer_evaluation_metrics.accuracy",
            "direction":"desc"
        }
    ]
}

Query: Find models with the lowest latency
Columns: ['output.model_latency.mean']
Output: {
    "sort_by" : [
        {
            "field":"output.model_latency.mean",
            "direction":"asc"
        }
    ]
}

Query: Return the rows in ascending order of the model precision
Columns: ['output.HalluScorerEvaluator.scorer_evaluation_metrics.precision']
Output: {
    "sort_by" : [
        {
            "field":"output.HalluScorerEvaluator.scorer_evaluation_metrics.precision",
            "direction":"asc"
        }
    ]
}

Query: {{query}}
Columns: {{columns}}
Output:
"""