"""CLI interface utilities for SakaiBot."""

import asyncio
from typing import List, Dict, Any, Union, Optional

from ..utils.logging import get_logger


class CLIInterface:
    """Handles CLI display and user input operations."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
    
    async def get_user_input(self, prompt: str) -> str:
        """Get user input asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, input, prompt)
    
    async def get_user_choice(
        self, 
        prompt: str = "Enter your choice: ", 
        expect_int: bool = True
    ) -> Union[int, str]:
        """Get user choice with validation."""
        while True:
            try:
                choice_str = await self.get_user_input(prompt)
                
                if not choice_str.strip() and expect_int:
                    print("Input cannot be empty. Please enter a number.")
                    continue
                
                if expect_int:
                    return int(choice_str)
                return choice_str.strip()
            
            except ValueError:
                if expect_int:
                    self._logger.warning(f"Invalid input '{choice_str}'. Please enter a number.")
                    print(f"Invalid input '{choice_str}'. Please enter a number.")
            except Exception as e:
                self._logger.error(f"Error getting user input: {e}", exc_info=True)
                if expect_int:
                    return -1
                return ""
    
    def print_header(self, title: str, width: int = 50) -> None:
        """Print a formatted header."""
        padding = max(0, width - len(title) - 10)
        print(f"\n{'=' * 5} {title} {'=' * padding}")
    
    def print_footer(self, width: int = 50) -> None:
        """Print a formatted footer."""
        print(f"{'=' * width}")
    
    def display_main_menu(self, cli_state) -> None:
        """Display the main menu."""
        pv_status = f"(Default Context PV: '{cli_state.get_pv_display_name()}')"
        group_status = cli_state.get_group_status_text()
        monitoring_status = cli_state.get_monitoring_status()
        auth_count = len(cli_state.directly_authorized_pvs)
        
        print("\nSakaiBot Menu:")
        print("=" * 30)
        print("--- Private Chat (PV) Management ---")
        print("1. List All Cached Private Chats (PVs)")
        print("2. Refresh/Update PV List from Telegram (Recent Chats)")
        print("3. Search PVs (from cached list)")
        print(f"4. Set Default PV Context (for /analyze) {pv_status}")
        print("--- Group & Categorization Management ---")
        print(f"5. Set/Change Categorization Target Group {group_status}")
        print("6. Manage Categorization Command Mappings")
        print(f"8. Manage Directly Authorized PVs ({auth_count} authorized)")
        print("--- Monitoring ---")
        print(f"7. {monitoring_status} (for categorization & AI commands)")
        print("   (Bot listens to your outgoing commands AND commands from authorized PVs)")
        print("=" * 30)
        print("0. Exit (Save Settings)")
    
    def display_entity_list(
        self,
        entity_list: List[Dict[str, Any]],
        title: str,
        entity_type: str = "PV",
        show_numbers: bool = True
    ) -> bool:
        """Display a formatted list of entities (PVs or Groups)."""
        if not entity_list:
            print(f"\nNo {entity_type}(s) to display.")
            return False
        
        self.print_header(title)
        
        # Define column widths
        idx_width = 5 if show_numbers else 2
        name_width = 30
        secondary_width = 25
        id_width = 15
        
        # Print headers
        if entity_type == "PV":
            header_format = "{:<{idx}} {:<{name}} {:<{secondary}} {:<{id}}"
            print(header_format.format(
                "No." if show_numbers else "",
                "Display Name",
                "Username",
                "User ID",
                idx=idx_width,
                name=name_width,
                secondary=secondary_width,
                id=id_width
            ))
        elif entity_type == "Group":
            header_format = "{:<{idx}} {:<{name}} {:<{type_}} {:<{id}}"
            print(header_format.format(
                "No." if show_numbers else "",
                "Group Title",
                "Type",
                "Group ID",
                idx=idx_width,
                name=name_width,
                type_=secondary_width,
                id=id_width
            ))
        
        print("-" * (idx_width + name_width + secondary_width + id_width + 3))
        
        # Print entities
        for index, item in enumerate(entity_list):
            prefix = f"{index + 1}." if show_numbers else "-"
            item_id = item['id']
            
            if entity_type == "PV":
                display_name = item.get('display_name', 'N/A')
                username = item.get('username', "N/A")
                print(header_format.format(
                    prefix,
                    display_name[:name_width-1],
                    username[:secondary_width-1] if username else "N/A",
                    str(item_id)[:id_width-1],
                    idx=idx_width,
                    name=name_width,
                    secondary=secondary_width,
                    id=id_width
                ))
            elif entity_type == "Group":
                title = item.get('title', 'N/A')
                group_type = "Forum" if item.get('is_forum') else "Regular"
                print(header_format.format(
                    prefix,
                    title[:name_width-1],
                    group_type,
                    str(item_id)[:id_width-1],
                    idx=idx_width,
                    name=name_width,
                    type_=secondary_width,
                    id=id_width
                ))
        
        self.print_footer()
        return True
    
    def display_topic_list(
        self,
        topics: List[Dict[str, Any]],
        group_title: str,
        show_numbers: bool = True
    ) -> bool:
        """Display a formatted list of topics."""
        if not topics:
            print(f"\nNo topics to display for '{group_title}'.")
            return False
        
        self.print_header(f"Topics in '{group_title}'")
        
        idx_width = 5 if show_numbers else 2
        title_width = 60
        id_width = 15
        
        header_format = "{:<{idx}} {:<{title}} {:<{id}}"
        print(header_format.format(
            "No." if show_numbers else "",
            "Topic Title",
            "Topic ID",
            idx=idx_width,
            title=title_width,
            id=id_width
        ))
        
        print("-" * (idx_width + title_width + id_width + 2))
        
        for index, topic in enumerate(topics):
            prefix = f"{index + 1}." if show_numbers else "-"
            topic_id = topic['id']
            topic_title = topic.get('title', 'N/A')
            
            print(header_format.format(
                prefix,
                topic_title[:title_width-1],
                str(topic_id)[:id_width-1],
                idx=idx_width,
                title=title_width,
                id=id_width
            ))
        
        self.print_footer()
        return True
    
    def display_command_mappings(
        self,
        command_mappings: Dict[str, Optional[int]],
        topics_cache: List[Dict[str, Any]],
        is_forum: bool,
        show_numbers: bool = False
    ) -> None:
        """Display current command mappings."""
        if not command_mappings:
            print("\nNo categorization command mappings currently defined.")
            return
        
        self.print_header("Current Categorization Command Mappings")
        
        cmd_width = 20
        target_width = 45
        
        if show_numbers:
            print(f"{'#':<4} {'Command':<{cmd_width}} {'Target':<{target_width}}")
            print(f"{'-'*4} {'-'*cmd_width} {'-'*target_width}")
        else:
            print(f"{'Command':<{cmd_width}} {'Target':<{target_width}}")
            print(f"{'-'*cmd_width} {'-'*target_width}")
        
        for index, (command, topic_id) in enumerate(command_mappings.items()):
            if topic_id is None:
                target_description = "Main Group Chat"
            elif is_forum:
                topic_title = next(
                    (t['title'] for t in topics_cache if t['id'] == topic_id),
                    f"Unknown Topic (ID: {topic_id})"
                )
                target_description = f"Topic: '{topic_title}' (ID: {topic_id})"
            else:
                target_description = f"Target ID: {topic_id} (Error: Non-forum group with topic ID)"
            
            if show_numbers:
                print(f"{index + 1:<4} /{command:<{cmd_width-1}} {target_description:<{target_width}}")
            else:
                print(f"/{command:<{cmd_width-1}} {target_description:<{target_width}}")
        
        self.print_footer()
    
    async def wait_for_continue(self) -> None:
        """Wait for user to press Enter to continue."""
        await self.get_user_input("\nPress Enter to continue...")
