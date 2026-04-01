from . import __version__ as app_version

app_name = "my_ai_assistant"
app_title = "My AI"
app_publisher = "AI"
app_description = "AI Assistant for ERPNext"
app_email = "ai@gmail.com"
app_license = "mit"

# v2.0.0 - Updated paths
app_include_css = "/assets/my_ai_assistant/css/ai_chat.css"
app_include_js = "/assets/my_ai_assistant/js/ai_chat.js"

fixtures = [
    {
        "doctype": "Page",
        "filters": [["name", "in", ["ai-chat"]]]
    }
]
