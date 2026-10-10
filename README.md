# DevMate — AI-Powered Coding Companion

DevMate is an AI-powered coding assistant built with Python, LangChain, Groq, and Streamlit. It provides a conversational interface for managing project files, writing and executing Python code, undoing file changes, and performing Git operations.

The project focuses on making common development tasks easier while introducing approval workflows for potentially destructive file operations.

## Features

- **AI-Powered Assistance:** Interact with an AI agent through a chat-based interface.
- **File Management:** List files, read file contents, and create new files within the designated workspace.
- **Approval-Based Editing:** Review proposed changes and approve or cancel overwrites of existing files.
- **Deletion Confirmation:** Request approval before deleting files.
- **Python Execution:** Run Python files and inspect their output and errors.
- **Undo Support:** Restore files from locally stored backups.
- **Git Integration:** Check repository status and create commits.
- **File Protection:** Encrypt and decrypt files using password-derived encryption keys.
- **Interactive Interface:** Use a Streamlit application to interact with the coding assistant.

## Technology Stack

- Python
- LangChain
- Groq API
- Streamlit
- Cryptography
- Git

## Project Structure

```text
BCSF24M016_TASK/
├── app.py
├── starter.py
├── llm.py
├── implementation_plan.txt
├── README.md
├── .gitignore
├── .env.example
└── work_dir/
    └── .history/
```

- `app.py` — Streamlit user interface and chat interaction.
- `starter.py` — Tool definitions for file management, execution, backups, Git, and file protection.
- `llm.py` — LLM configuration, system instructions, and agent initialization.
- `implementation_plan.txt` — Project planning and implementation notes.
- `.env.example` — Template for required environment variables.
- `work_dir/` — Workspace for files managed by the assistant.
- `work_dir/.history/` — Local file backups used for restoration.

The exact contents of the workspace may vary as files are created during use.

## Prerequisites

Before running DevMate, make sure you have:

- Python 3.9 or newer.
- Git installed.
- A Groq API key.
- An internet connection for API requests.

## Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd BCSF24M016_TASK
```

Replace `<your-repository-url>` with your GitHub repository URL. If you are using only a local repository, open a terminal in your existing project directory instead.

### 2. Create a virtual environment

On Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, activate the environment using Command Prompt or resolve the execution-policy issue according to your system's configuration.

### 3. Install dependencies

If a `requirements.txt` file is available:

```bash
python -m pip install -r requirements.txt
```

Otherwise, install the packages used by the project:

```bash
python -m pip install streamlit langchain langchain-groq python-dotenv cryptography
```

### 4. Configure environment variables

Create a `.env` file in the project root and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Obtain an API key from the Groq Console:

https://console.groq.com/

Never commit your real `.env` file or expose your API key publicly.

### 5. Run the application

```bash
python -m streamlit run app.py
```

Streamlit will provide a local URL in the terminal. Open that URL in your browser to use DevMate.

## Usage

1. Launch the application.
2. Enter a coding or file-management request in the chat.
3. Review the assistant's response and proposed actions.
4. Approve or cancel file overwrites and deletions when prompted.
5. Inspect Python execution results and errors.
6. Use Git tools to inspect repository status and manage commits.

Example requests:

```text
List the files in my workspace.
Create a Python file that prints prime numbers.
Run primes.py and show its output.
Edit primes.py to print prime numbers from 1 to 100.
Show the current Git status.
Undo the most recent backed-up version of primes.py.
```

## Workspace and Safety

DevMate uses a designated workspace for its file-management tools. These tools validate file paths to help prevent access outside the workspace.

Existing-file overwrites and file deletions use approval workflows. Backups can help restore previous file contents.

However, these safeguards do not constitute a complete security sandbox. Executing Python code can still have system-level effects, and some operations, such as encryption or Git commits, may modify files or repository state directly. Only run code you trust, and keep independent backups of important data.

## Security Notes

- Store API keys in environment variables.
- Keep `.env` out of version control.
- Do not commit passwords, credentials, or sensitive files.
- Use strong passwords when encrypting files.
- Keep backups of important project data.
- Review code before executing it.

## Current Scope

DevMate is a learning and development project demonstrating AI agents, tool calling, file-system operations, approval workflows, Python execution, and Git integration.

Its safeguards reduce the risk of accidental changes but should not be treated as production-grade isolation or security controls.

## License

No license has been specified yet. Add a license file if you intend to distribute or permit reuse of this project.
