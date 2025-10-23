"""AutoFix Dashboard - Premium Dark Theme with AI Metrics"""
import reflex as rx
from datetime import datetime


class State(rx.State):
    """Dashboard state with AutoFix metrics"""
    
    # Basic metrics
    total_runs: int = 127
    fixed_errors: int = 89
    failed_fixes: int = 38
    handler_fixes: int = 71
    ai_fixes: int = 18
    
    # AI Usage metrics
    ai_requests_used: int = 18
    ai_requests_limit: int = 50
    estimated_cost_saved: float = 2.45
    avg_handler_time: float = 0.5
    avg_ai_time: float = 7.2
    
    # Recent runs
    recent_runs: list[dict] = [
        {"timestamp": "2025-10-23 20:15", "error_type": "SyntaxError", "status": "fixed", "method": "handler", "time": "0.5s"},
        {"timestamp": "2025-10-23 20:10", "error_type": "ModuleNotFoundError", "status": "failed", "method": "handler", "time": "0.8s"},
        {"timestamp": "2025-10-23 20:05", "error_type": "ImportError", "status": "fixed", "method": "gemini", "time": "7.2s"},
        {"timestamp": "2025-10-23 20:00", "error_type": "TypeError", "status": "fixed", "method": "handler", "time": "0.4s"},
        {"timestamp": "2025-10-23 19:55", "error_type": "IndentationError", "status": "fixed", "method": "handler", "time": "0.3s"},
    ]
    
    last_updated: str = datetime.now().strftime("%H:%M:%S")
    is_live: bool = True
    
    @rx.var
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return round((self.fixed_errors / self.total_runs) * 100, 1)
    
    @rx.var
    def handler_percentage(self) -> float:
        if self.fixed_errors == 0:
            return 0.0
        return round((self.handler_fixes / self.fixed_errors) * 100, 1)
    
    @rx.var
    def ai_usage_percentage(self) -> int:
        return int(round((self.ai_requests_used / self.ai_requests_limit) * 100))
    
    def refresh_data(self):
        self.last_updated = datetime.now().strftime("%H:%M:%S")


def gradient_card(title: str, value, subtitle: str, icon: str, gradient_from: str, gradient_to: str, trend: str = None) -> rx.Component:
    """Premium gradient card"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=28, color="white"),
                rx.spacer(),
                rx.cond(
                    trend,
                    rx.badge(rx.icon("trending-up", size=12), trend, color_scheme="green", variant="soft"),
                    rx.text(""),
                ),
                width="100%",
            ),
            rx.text(value, size="9", font_weight="bold", color="white", margin_top="12px"),
            rx.text(title, size="3", font_weight="600", color="rgba(255,255,255,0.9)"),
            rx.text(subtitle, size="2", color="rgba(255,255,255,0.6)"),
            spacing="2",
            align="start",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background=f"linear-gradient(135deg, {gradient_from} 0%, {gradient_to} 100%)",
        box_shadow="0 8px 32px rgba(0,0,0,0.3)",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 12px 48px rgba(0,0,0,0.4)", "transition": "all 0.3s ease"},
    )


def ai_usage_card() -> rx.Component:
    """AI Usage metrics card"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("cpu", size=28, color="white"),
                rx.spacer(),
                rx.badge(State.ai_requests_used, " / ", State.ai_requests_limit, " requests", color_scheme="purple", variant="soft"),
                width="100%",
            ),
            rx.text("AI Usage (Gemini)", size="4", font_weight="600", color="rgba(255,255,255,0.9)", margin_top="12px"),
            rx.box(
                rx.progress(value=State.ai_usage_percentage, max=100, color_scheme="purple", height="8px", width="100%"),
                width="100%",
            ),
            rx.hstack(
                rx.text(State.ai_usage_percentage, "% used", size="2", color="rgba(255,255,255,0.7)"),
                rx.spacer(),
                rx.text(State.ai_requests_limit - State.ai_requests_used, " remaining", size="2", color="rgba(255,255,255,0.5)"),
                width="100%",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background="linear-gradient(135deg, #667EEA 0%, #764BA2 100%)",
        box_shadow="0 8px 32px rgba(0,0,0,0.3)",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 12px 48px rgba(0,0,0,0.4)", "transition": "all 0.3s ease"},
    )


def cost_savings_card() -> rx.Component:
    """Cost savings card"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("dollar-sign", size=28, color="white"),
                rx.spacer(),
                rx.badge("Saved", color_scheme="green", variant="soft"),
                width="100%",
            ),
            rx.hstack(
                rx.text("$", size="8", font_weight="bold", color="white", margin_top="12px"),
                rx.text(State.estimated_cost_saved, size="9", font_weight="bold", color="white", margin_top="12px"),
                spacing="1",
            ),
            rx.text("Cost Savings", size="3", font_weight="600", color="rgba(255,255,255,0.9)"),
            rx.text("By using handlers", size="2", color="rgba(255,255,255,0.6)"),
            spacing="2",
            align="start",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background="linear-gradient(135deg, #11998E 0%, #38EF7D 100%)",
        box_shadow="0 8px 32px rgba(0,0,0,0.3)",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 12px 48px rgba(0,0,0,0.4)", "transition": "all 0.3s ease"},
    )


def speed_card() -> rx.Component:
    """Speed comparison card"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("zap", size=28, color="white"),
                rx.spacer(),
                rx.badge("14.4x faster", color_scheme="yellow", variant="soft"),
                width="100%",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Handler:", size="2", color="rgba(255,255,255,0.7)"),
                    rx.spacer(),
                    rx.text(State.avg_handler_time, "s", size="2", font_weight="bold", color="white"),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("AI (Gemini):", size="2", color="rgba(255,255,255,0.7)"),
                    rx.spacer(),
                    rx.text(State.avg_ai_time, "s", size="2", font_weight="bold", color="white"),
                    width="100%",
                ),
                spacing="2",
                width="100%",
                margin_top="12px",
            ),
            rx.text("Speed Comparison", size="3", font_weight="600", color="rgba(255,255,255,0.9)", margin_top="8px"),
            rx.text("Average execution time", size="2", color="rgba(255,255,255,0.6)"),
            spacing="2",
            align="start",
            width="100%",
        ),
        padding="24px",
        border_radius="16px",
        background="linear-gradient(135deg, #F093FB 0%, #F5576C 100%)",
        box_shadow="0 8px 32px rgba(0,0,0,0.3)",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 12px 48px rgba(0,0,0,0.4)", "transition": "all 0.3s ease"},
    )

# ... (המשך מהחלק 1)


def sidebar() -> rx.Component:
    """Dark sidebar navigation"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("code-2", size=32, color="#00D9FF"),
                rx.heading("AutoFix", size="7", color="white"),
                spacing="3",
                margin_bottom="32px",
            ),
            rx.divider(color_scheme="gray"),
            rx.vstack(
                rx.link(
                    rx.hstack(
                        rx.icon("layout-dashboard", size=20, color="white"),
                        rx.text("Dashboard", size="3", color="white"),
                        spacing="3",
                    ),
                    href="/",
                    padding="12px 16px",
                    border_radius="8px",
                    background="rgba(0,217,255,0.1)",
                    border_left="3px solid #00D9FF",
                    width="100%",
                ),
                rx.link(
                    rx.hstack(
                        rx.icon("activity", size=20, color="rgba(255,255,255,0.6)"),
                        rx.text("Analytics", size="3", color="rgba(255,255,255,0.6)"),
                        spacing="3",
                    ),
                    href="/analytics",
                    padding="12px 16px",
                    border_radius="8px",
                    _hover={"background": "rgba(255,255,255,0.05)"},
                    width="100%",
                ),
                rx.link(
                    rx.hstack(
                        rx.icon("history", size=20, color="rgba(255,255,255,0.6)"),
                        rx.text("History", size="3", color="rgba(255,255,255,0.6)"),
                        spacing="3",
                    ),
                    href="/history",
                    padding="12px 16px",
                    border_radius="8px",
                    _hover={"background": "rgba(255,255,255,0.05)"},
                    width="100%",
                ),
                rx.link(
                    rx.hstack(
                        rx.icon("settings", size=20, color="rgba(255,255,255,0.6)"),
                        rx.text("Settings", size="3", color="rgba(255,255,255,0.6)"),
                        spacing="3",
                    ),
                    href="/settings",
                    padding="12px 16px",
                    border_radius="8px",
                    _hover={"background": "rgba(255,255,255,0.05)"},
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            rx.spacer(),
            rx.box(
                rx.vstack(
                    rx.text("System Status", size="2", color="rgba(255,255,255,0.5)", font_weight="600"),
                    rx.hstack(
                        rx.box(width="8px", height="8px", border_radius="50%", background="#00FF88"),
                        rx.text("Online", size="2", color="#00FF88"),
                        spacing="2",
                    ),
                    rx.text("Uptime: 14d 06:42", size="1", color="rgba(255,255,255,0.4)"),
                    align="start",
                    spacing="2",
                ),
                padding="16px",
                border_radius="12px",
                background="rgba(255,255,255,0.05)",
                width="100%",
            ),
            spacing="6",
            align="start",
            height="100%",
        ),
        width="280px",
        height="100vh",
        padding="24px",
        background="linear-gradient(180deg, #0F172A 0%, #1E293B 100%)",
        border_right="1px solid rgba(255,255,255,0.1)",
        position="fixed",
        top="0",
        left="0",
    )


def topbar() -> rx.Component:
    """Premium top bar"""
    return rx.hstack(
        rx.hstack(
            rx.badge(rx.icon("circle", size=8, fill="current"), "LIVE", color_scheme="green", variant="soft", size="2"),
            rx.hstack(
                rx.text("Last updated: ", size="2", color="rgba(255,255,255,0.6)"),
                rx.text(State.last_updated, size="2", color="rgba(255,255,255,0.6)"),
                spacing="1",
            ),
            spacing="3",
        ),
        rx.spacer(),
        rx.button(
            rx.icon("refresh-cw", size=16),
            "Refresh",
            on_click=State.refresh_data,
            size="2",
            color_scheme="cyan",
            variant="soft",
        ),
        padding="20px 32px",
        border_bottom="1px solid rgba(255,255,255,0.1)",
        background="rgba(15,23,42,0.8)",
        backdrop_filter="blur(12px)",
        width="100%",
        align="center",
    )


def premium_table() -> rx.Component:
    """Premium table"""
    return rx.box(
        rx.vstack(
            rx.heading("Recent Runs", size="6", color="white"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Timestamp", color="rgba(255,255,255,0.6)"),
                        rx.table.column_header_cell("Error Type", color="rgba(255,255,255,0.6)"),
                        rx.table.column_header_cell("Status", color="rgba(255,255,255,0.6)"),
                        rx.table.column_header_cell("Method", color="rgba(255,255,255,0.6)"),
                        rx.table.column_header_cell("Time", color="rgba(255,255,255,0.6)"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        State.recent_runs,
                        lambda run: rx.table.row(
                            rx.table.cell(run["timestamp"], color="white"),
                            rx.table.cell(rx.code(run["error_type"], size="2", color_scheme="cyan")),
                            rx.table.cell(
                                rx.badge(
                                    run["status"],
                                    color_scheme=rx.cond(run["status"] == "fixed", "green", "red"),
                                    variant="soft",
                                ),
                            ),
                            rx.table.cell(
                                rx.badge(
                                    run["method"],
                                    color_scheme=rx.cond(run["method"] == "handler", "blue", "purple"),
                                    variant="soft",
                                ),
                            ),
                            rx.table.cell(run["time"], color="rgba(255,255,255,0.7)"),
                            _hover={"background": "rgba(0,217,255,0.05)"},
                        ),
                    ),
                ),
                width="100%",
                variant="surface",
            ),
            spacing="4",
            align="start",
        ),
        padding="24px",
        border_radius="16px",
        background="rgba(15,23,42,0.6)",
        border="1px solid rgba(255,255,255,0.1)",
        box_shadow="0 8px 32px rgba(0,0,0,0.3)",
    )


def index() -> rx.Component:
    """Premium dark dashboard with AI metrics"""
    return rx.box(
        rx.hstack(
            sidebar(),
            rx.box(
                rx.vstack(
                    topbar(),
                    rx.box(
                        rx.vstack(
                            # Row 1: Main Stats
                            rx.grid(
                                gradient_card("Total Runs", State.total_runs, "All time executions", "activity", "#667EEA", "#764BA2", "+12%"),
                                gradient_card("Fixed Errors", State.fixed_errors, "70.1% success rate", "check-circle", "#11998E", "#38EF7D", "+8%"),
                                gradient_card("Failed Fixes", State.failed_fixes, "Require attention", "alert-triangle", "#E53935", "#E35D5B", "-3%"),
                                gradient_card("Handler Fixes", State.handler_fixes, "79.8% of total", "zap", "#F093FB", "#F5576C", "+15%"),
                                columns="4",
                                gap="20px",
                                width="100%",
                            ),
                            # Row 2: AI Metrics
                            rx.grid(
                                ai_usage_card(),
                                cost_savings_card(),
                                speed_card(),
                                columns="3",
                                gap="20px",
                                width="100%",
                            ),
                            # Table
                            premium_table(),
                            spacing="6",
                        ),
                        padding="32px",
                    ),
                    spacing="0",
                    width="100%",
                ),
                margin_left="280px",
                min_height="100vh",
                background="linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)",
            ),
            spacing="0",
            width="100%",
            align="start",
        ),
        width="100%",
        background="#0F172A",
    )


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="cyan",
    )
)

app.add_page(index, route="/")
