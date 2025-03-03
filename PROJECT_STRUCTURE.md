# Audio Query Processor - Project Structure

```
audio_query_processor/
├── main.py                  # Main Streamlit application
│   ├── main()               # Main application function
│   ├── apply_custom_css()   # Apply custom styling
│   ├── display_header()     # Display application header
│   ├── initialize_session_state() # Initialize session variables
│   ├── display_recording_controls() # Display recording UI
│   ├── display_recording_progress() # Show recording progress
│   ├── process_audio_file() # Process recorded audio
│   ├── display_results()    # Display query results
│   └── reset_session_state() # Reset application state
│
├── utils.py                 # Utility functions
│   ├── render_prompt()      # Render prompt templates
│   ├── audio2text()         # Transcribe audio to text
│   ├── audio_callback()     # Audio recording callback
│   ├── start_recording()    # Start audio recording
│   ├── stop_recording()     # Stop audio recording
│   ├── record_audio()       # Record audio for fixed duration
│   ├── get_fields_description() # Get database field descriptions
│   ├── generate_response()  # Generate responses using OpenAI
│   └── call_weave()         # Execute queries against Weave
│
├── evals.py                 # Evaluation functionality
│   ├── QueryEvalModel       # Model for evaluating query accuracy
│   │   └── predict()        # Generate query from user input
│   ├── query_accuracy_score() # Calculate accuracy score
│   └── evaluation           # Weave evaluation instance
│
├── prompts.py               # Prompt templates
│   ├── COLUMN_SELECTION_PROMPT # Template for column selection
│   ├── QUERY_PROMPT         # Template for query generation
│   └── SORT_BY_PROMPT       # Template for sort criteria
│
├── columns.json             # Database column descriptions
├── requirements.txt         # Project dependencies
├── .env                     # Environment variables
├── .gitignore               # Git ignore patterns
├── LICENSE                  # Project license
└── README.md                # Project documentation
```

## Module Relationships

- `main.py` depends on `utils.py` for audio processing and query generation
- `utils.py` depends on `prompts.py` for prompt templates
- `evals.py` depends on `utils.py` for query generation and `prompts.py` for templates
- All modules access `columns.json` for database field descriptions

## Data Flow

1. User speaks a query through the Streamlit interface
2. Audio is recorded and transcribed to text
3. Text is processed to identify required columns
4. A database query is generated based on the text and columns
5. The query is executed against the Weave database
6. Results are displayed to the user

## Environment Variables

- `OPENAI_API_KEY`: API key for OpenAI services
- `WEAVE_PROJECT_NAME`: Name of the Weave project
- `WEAVE_DB_PROJECT`: Weave database project identifier
- `SAMPLE_RATE`: Audio sample rate for recording 