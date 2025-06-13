# Kusto MCP Server for VS Code + GitHub Copilot

Connect your Kusto database to GitHub Copilot in VS Code for intelligent data querying!

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
# Activate virtual environment
venv\Scripts\activate

# Install all required packages from requirements.txt
pip install -r requirements.txt
```

### 2. Configure Your Cluster
Edit `config/config.json` with your Kusto cluster details:
```json
{
  "clusters": {
    "production": {
      "url": "${KUSTO_CLUSTER_URL}",
      "database": "${KUSTO_DATABASE}"
    }
  },
  "logging": {
    "level": "INFO",
    "file": "logs/mcp-kusto-server.log"
  },
  "settings": {
    "default_limit": 1000,
    "timeout_seconds": 30
  }
}
```

put in the kusto information in .env file

### 3. Pre-Authenticate
```bash
python pre_auth.py
```
- Choose **Option 2 (Interactive Browser)**
- Your browser will open for Microsoft authentication
- Sign in with your Microsoft work account
- This caches your credentials for VS Code

### 4. Configure VS Code MCP Settings
1. **Open Command Palette** (`Ctrl+Shift+P`)
2. **Type:** "MCP: Open MCP Settings" 
3. **Navigate to** `.vscode/mcp.json`
4. **Add your server configuration:**


```json
{
    "servers": {
        "kusto": {
            "command": "your-location/mcp-kusto-server/venv/Scripts/python.exe",
            "args": ["your-location/mcp-kusto-server/mcp_server_cached_auth.py"],
            "env": {
                "KUSTO_CONFIG_FILE": "your-location/mcp-kusto-server/config/config.json"
            }
        }
    }
}
```

**⚠️ Update the paths to match your actual file locations!**

### 5. Start the MCP Server in VS Code
1. **Go to** `.vscode/mcp.json` (or wherever your MCP settings are)
2. **Find your "kusto" server** in the list
3. **Click "Start"** to start the server
4. **Verify** it shows as "Running"

### 6. Enable Copilot Agent Mode
1. **Open GitHub Copilot Chat** (sidebar or `Ctrl+Shift+I`)
2. **Enable Agent Mode** (toggle switch in chat interface)
3. **Verify** Copilot can see your MCP tools

## 🎯 Usage Examples

Once everything is running, ask Copilot:

```
"List all tables in my Kusto database"

"Show me the schema of the Users table" 

"Query the Events table for errors in the last hour"

"Find the top 10 most active users in the UserActivity table"

"Analyze trends in the LogEntries table over the past week"
```

## 🔧 Available Tools

Your Copilot now has access to:
- **execute_kql** - Run any KQL query
- **list_tables** - Show available tables  
- **get_table_schema** - Get table structure

## 🔍 Troubleshooting

### Authentication Issues
- Run `python pre_auth.py` again
- Try **Option 2 (Interactive Browser)** authentication
- Make sure you can access your cluster in Azure Data Explorer UI

### VS Code Issues  
- Check that MCP server shows as "Running" in `.vscode/mcp.json`
- Restart VS Code after configuration changes
- Check paths in your configuration are correct

### Copilot Not Seeing Tools
- Ensure Copilot is in **Agent Mode**
- Restart Copilot Chat window
- Check that MCP server is started and running

## 📦 Requirements File

Make sure your `requirements.txt` includes:
```
azure-kusto-data
azure-identity
mcp
asyncio-compat
pathlib-abc
typing-extensions
```

## 📝 Files Created

- `mcp_server_cached_auth.py` - Main MCP server (uses cached auth)
- `pre_auth.py` - Authentication helper (run this first)
- `config/config.json` - Cluster configuration
- `logs/mcp-kusto-cached-auth.log` - Server logs
- `requirements.txt` - Python dependencies

## 🎉 Success!

When everything works, you can ask Copilot to help you:
- Write complex KQL queries
- Analyze your data patterns
- Explore your database schema
- Generate insights from your Kusto data

All directly from VS Code! 🚀

---

**Need help?** Check the log file: `logs/mcp-kusto-cached-auth.log`