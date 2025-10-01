# 🎛️ Interactive Menu Guide

## How to Use the New Interactive Menu System

### **Quick Start**

#### Option 1: Direct Interactive Menu
```bash
sakaibot menu
```

#### Option 2: Choose from Main Menu
```bash
sakaibot
# Then select option [1] for Interactive Menu
```

### **Navigation**

- **Use numbers** to select options (1, 2, 3, etc.)
- **Use 0** to go back to previous menu
- **Use Ctrl+C** to go back (same as 0)
- **Press Enter** after typing your choice

### **Menu Structure**

```
🤖 SakaiBot Interactive Menu
├── 1. 📱 Private Chats (PVs)
│   ├── List cached PVs (with pagination)
│   ├── Refresh from Telegram
│   ├── Search PVs (by name, username, ID)
│   ├── Set default context PV
│   └── Analyze messages (Persian sarcasm! 😏)
│
├── 2. 👥 Groups & Categories
│   ├── Set target group
│   ├── Manage command mappings
│   └── List groups
│
├── 3. 🤖 AI Tools
│   ├── Test AI connection
│   ├── Translate with Persian phonetics
│   ├── Custom prompts
│   └── Persian analysis demo
│
├── 4. 📊 Monitoring
│   ├── Start/Stop monitoring
│   ├── Manage authorized users
│   └── View monitor status
│
└── 5. ⚙️ Settings
    ├── View configuration
    ├── Edit settings
    └── Clear cache
```

### **Persian Sarcastic Analysis** 🎭

The new Persian analysis feature provides:
- **Documentary-style narrator voice** (like The Office)
- **Character archetypes** ("the know-it-all", "the yes-man")
- **Probability predictions** for follow-up actions
- **Observational humor** about human communication patterns

Access via: **Menu → Private Chats → Analyze Messages**

### **Status Bar Information**

At the top of each menu, you'll see:
- **AI Provider**: Current AI provider and model
- **Group**: Selected target group for categorization  
- **Auth**: Number of authorized users
- **Monitor**: Monitoring status (ON/OFF)

### **Features Implemented**

✅ **Working Now:**
- Full interactive navigation
- PV list display with pagination
- PV search functionality
- Settings management
- Beautiful Rich-based UI
- Status information
- Error handling

🚧 **Coming Soon:**
- Real Telegram integration for PV refresh
- Complete Persian sarcastic analysis
- Group management
- Monitoring controls
- AI tool integration

### **Tips**

1. **Navigation**: You can always go back with 0 or Ctrl+C
2. **Search**: Use partial names, usernames, or IDs when searching PVs
3. **Pagination**: When viewing PV lists, you can choose to see more results
4. **Settings**: All your selections are automatically saved
5. **Exit**: Use option 0 from main menu to exit and save settings

### **Examples**

#### Search and Select a PV:
```
sakaibot menu
[1] → [3] → Enter "john" → Select from results → [2] Analyze messages
```

#### Set Target Group:
```
sakaibot menu
[2] → [1] → Select group from list
```

#### Test Persian Analysis:
```
sakaibot menu
[3] → [4] → See demo of sarcastic analysis style
```

Enjoy your new interactive CLI experience! 🤖✨