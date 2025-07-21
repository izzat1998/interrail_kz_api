#!/usr/bin/env python3
"""
🚀 Interactive Telegram CI/CD Notification System
Transforms your boring CI/CD pipeline into an engaging interactive experience!
"""

import json
import os
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramNotifier:
    """🤖 Creative Telegram notification system with interactive features"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.thread_id = os.getenv("TELEGRAM_THREAD_ID")
        self.notification_level = os.getenv("NOTIFICATION_LEVEL", "standard")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # Validate required environment variables
        if not self.bot_token or not self.chat_id:
            raise ValueError("🚨 TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set!")

    def send_request(self, method: str, data: dict) -> dict:
        """Send HTTP request to Telegram API with error handling"""
        url = f"{self.base_url}/{method}"

        try:
            # Add chat_id and thread_id to all requests
            data["chat_id"] = self.chat_id
            if self.thread_id:
                data["message_thread_id"] = self.thread_id

            # Encode data
            encoded_data = urlencode(data).encode("utf-8")
            request = Request(url, data=encoded_data, method="POST")  # noqa: S310
            request.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urlopen(request) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))

        except (URLError, HTTPError) as e:
            error_details = {"ok": False, "error": str(e)}
            # Try to get more details from the response
            if hasattr(e, "read"):
                try:
                    error_body = e.read().decode("utf-8")
                    error_details["error_body"] = error_body
                except Exception:  # noqa: S110
                    pass
            return error_details

    def create_progress_bar(self, percentage: int) -> str:
        """🎨 Create simple progress bar"""
        filled = int(percentage / 10)
        bar = ""
        for i in range(10):
            if i < filled:
                bar += "🟢"
            elif i == filled and percentage % 10 >= 5:
                bar += "🟡"
            else:
                bar += "⚪"
        return f"{bar} {percentage}%"

    def create_inline_keyboard(self, buttons: list[dict]) -> dict:
        """🎮 Create interactive inline keyboard"""
        keyboard = []
        row = []

        for button in buttons:
            if len(row) >= 3:  # Max 3 buttons per row
                keyboard.append(row)
                row = []

            # Create button data - only include url OR callback_data, not both
            button_data = {"text": button["text"]}
            if button.get("url"):
                button_data["url"] = button["url"]
            elif button.get("callback_data"):
                button_data["callback_data"] = button["callback_data"]

            row.append(button_data)

        if row:
            keyboard.append(row)

        return {"inline_keyboard": keyboard}

    def format_duration(self, seconds: int) -> str:
        """⏱️ Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def send_pipeline_start(self, context: dict) -> int | None:
        """🚀 Send pipeline start notification"""
        repo = context.get("repository", "Unknown")
        branch = context.get("branch", "Unknown")
        commit = context.get("commit", "Unknown")[:8]
        author = context.get("author", "Unknown")
        workflow = context.get("workflow", "CI/CD")

        # Format start time properly
        start_time_raw = context.get("start_time")
        if start_time_raw and str(start_time_raw).isdigit():
            start_time = datetime.fromtimestamp(int(start_time_raw)).strftime(
                "%H:%M:%S"
            )
        else:
            start_time = datetime.now().strftime("%H:%M:%S")

        message = f"""
🚀 **{workflow} Pipeline Started!**

📁 **Repository:** `{repo}`
🌿 **Branch:** `{branch}`
📝 **Commit:** `{commit}`
👤 **Author:** {author}
⏰ **Started:** {start_time}

{self.create_progress_bar(0)}

🔄 *Initializing pipeline...*
        """.strip()

        buttons = [
            {"text": "📊 View Workflow", "url": context.get("workflow_url", "#")},
            {"text": "📝 View Commit", "url": context.get("commit_url", "#")},
            {"text": "🔍 Live Logs", "url": context.get("logs_url", "#")},
        ]

        data = {
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(self.create_inline_keyboard(buttons)),
        }

        response = self.send_request("sendMessage", data)
        if response.get("ok"):
            return response["result"]["message_id"]
        return None

    def update_pipeline_progress(
        self,
        message_id: int,
        step: str,
        progress: int,
        context: dict,
        status: str = "running",
    ) -> bool:
        """🔄 Update pipeline progress with animated indicators"""

        status_emojis = {
            "running": "🔄",
            "success": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "skipped": "⏭️",
        }

        repo = context.get("repository", "Unknown")
        branch = context.get("branch", "Unknown")
        commit = context.get("commit", "Unknown")[:8]
        author = context.get("author", "Unknown")
        workflow = context.get("workflow", "CI/CD")

        # Format start time properly
        start_time_raw = context.get("start_time")
        if start_time_raw and str(start_time_raw).isdigit():
            start_time = datetime.fromtimestamp(int(start_time_raw)).strftime(
                "%H:%M:%S"
            )
        else:
            start_time = datetime.now().strftime("%H:%M:%S")

        message = f"""
🚀 **{workflow} Pipeline Running**

📁 **Repository:** `{repo}`
🌿 **Branch:** `{branch}`
📝 **Commit:** `{commit}`
👤 **Author:** {author}
⏰ **Started:** {start_time}

{self.create_progress_bar(progress)}

{status_emojis.get(status, "🔄")} **Current Step:** {step}
        """.strip()

        # Add completed steps
        completed_steps = context.get("completed_steps", [])
        if completed_steps:
            message += "\n\n📋 **Completed Steps:**\n"
            for completed_step in completed_steps:
                message += f"✅ {completed_step}\n"

        # Add timing info
        if context.get("step_duration"):
            message += f"\n⏱️ **Step Duration:** {self.format_duration(context['step_duration'])}"

        buttons = [
            {"text": "📊 View Workflow", "url": context.get("workflow_url", "#")},
            {"text": "🔍 Live Logs", "url": context.get("logs_url", "#")},
        ]

        if status == "failed":
            buttons.append({"text": "🔄 Retry", "callback_data": "retry_pipeline"})

        data = {
            "message_id": message_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(self.create_inline_keyboard(buttons)),
        }

        response = self.send_request("editMessageText", data)
        return response.get("ok", False)

    def send_pipeline_success(self, message_id: int, context: dict) -> bool:
        """🎉 Send successful pipeline completion notification"""

        repo = context.get("repository", "Unknown")
        branch = context.get("branch", "Unknown")
        commit = context.get("commit", "Unknown")[:8]
        author = context.get("author", "Unknown")
        duration = context.get("total_duration", 0)
        coverage = context.get("coverage", 0)

        # Create celebration based on performance
        celebration = "🎉"
        if duration < 60:
            celebration = "🚀💨"
        elif duration < 180:
            celebration = "🎉✨"
        else:
            celebration = "🎉"

        # Coverage emoji
        coverage_emoji = "📊"
        if coverage >= 90:
            coverage_emoji = "🏆"
        elif coverage >= 80:
            coverage_emoji = "🥇"
        elif coverage >= 70:
            coverage_emoji = "🥈"
        else:
            coverage_emoji = "🥉"

        # Format test summary
        test_info = ""
        test_summary = context.get("test_summary")

        # Handle case where test_summary might be a JSON string
        if isinstance(test_summary, str):
            try:
                test_summary = json.loads(test_summary)
            except json.JSONDecodeError:
                test_summary = None

        if test_summary and isinstance(test_summary, dict):
            total_tests = test_summary.get("total_tests", 0)
            total_passed = test_summary.get("total_passed", 0)
            total_failed = test_summary.get("total_failed", 0)
            by_app = test_summary.get("by_app", {})

            test_info = f"🧪 **Tests:** {total_passed}/{total_tests} passed"
            if total_failed > 0:
                test_info += f" ({total_failed} failed)"

            if by_app:
                test_info += "\n📊 **By App:**\n"
                for app, stats in by_app.items():
                    passed = stats.get("passed", 0)
                    failed = stats.get("failed", 0)
                    total_app = passed + failed
                    emoji = "✅" if failed == 0 else "⚠️"
                    test_info += f"{emoji} {app}: {passed}/{total_app}\n"

        message = f"""
{celebration} **Pipeline Completed Successfully!**

📁 **Repository:** `{repo}`
🌿 **Branch:** `{branch}`
📝 **Commit:** `{commit}`
👤 **Author:** {author}

{self.create_progress_bar(100)}

✅ **Status:** All checks passed!
⏱️ **Duration:** {self.format_duration(duration)}
{coverage_emoji} **Coverage:** {coverage}%
{test_info}
🏗️ **Build:** Ready for deployment

📋 **Completed Steps:**
        """.strip()

        # Add timestamp to ensure message is unique
        message += f"\n\n⏰ **Completed at:** {datetime.now().strftime('%H:%M:%S')}"

        # Add all completed steps
        for step in context.get("completed_steps", []):
            message += f"\n✅ {step}"

        buttons = [
            {
                "text": "📊 Coverage Report",
                "url": str(context.get("coverage_url", "#")),
            },
            {"text": "📦 Artifacts", "url": str(context.get("artifacts_url", "#"))},
            {"text": "🔍 Full Logs", "url": str(context.get("logs_url", "#"))},
        ]

        data = {
            "message_id": message_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(self.create_inline_keyboard(buttons)),
        }

        print(f"DEBUG: Message length: {len(message)} characters")  # noqa: T201
        print(f"DEBUG: Message content: {message[:200]}...")  # noqa: T201
        response = self.send_request("editMessageText", data)
        if not response.get("ok", False):
            print(f"DEBUG: Telegram API error in success notification: {response}")  # noqa: T201
        return response.get("ok", False)

    def send_pipeline_failure(self, message_id: int, context: dict) -> bool:
        """💥 Send pipeline failure notification with diagnostics"""

        repo = context.get("repository", "Unknown")
        branch = context.get("branch", "Unknown")
        commit = context.get("commit", "Unknown")[:8]
        author = context.get("author", "Unknown")
        failed_step = context.get("failed_step", "Unknown")
        error_message = context.get("error_message", "No details available")
        duration = context.get("total_duration", 0)

        message = f"""
💥 **Pipeline Failed!**

📁 **Repository:** `{repo}`
🌿 **Branch:** `{branch}`
📝 **Commit:** `{commit}`
👤 **Author:** {author}

{self.create_progress_bar(context.get("progress", 50))}

❌ **Failed Step:** {failed_step}
⏱️ **Duration:** {self.format_duration(duration)}
💬 **Error:** `{error_message[:100]}...`

📋 **Completed Steps:**
        """.strip()

        # Add completed steps
        for step in context.get("completed_steps", []):
            message += f"\n✅ {step}"

        # Add failed step
        message += f"\n❌ {failed_step}"

        # Add quick fix suggestions
        suggestions = context.get("fix_suggestions", [])
        if suggestions:
            message += "\n\n💡 **Quick Fixes:**"
            for suggestion in suggestions[:3]:  # Limit to 3 suggestions
                message += f"\n• {suggestion}"

        buttons = [
            {"text": "🔄 Retry Pipeline", "callback_data": "retry_pipeline"},
            {"text": "🐛 View Error Logs", "url": context.get("error_logs_url", "#")},
            {"text": "💬 Report Issue", "url": context.get("issue_url", "#")},
            {"text": "📞 Get Help", "callback_data": "get_help"},
        ]

        data = {
            "message_id": message_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(self.create_inline_keyboard(buttons)),
        }

        response = self.send_request("editMessageText", data)
        return response.get("ok", False)

    def send_deployment_notification(self, context: dict) -> int | None:
        """🚀 Send deployment notification"""

        environment = context.get("environment", "production")
        status = context.get("status", "deploying")
        version = context.get("version", "latest")

        status_emojis = {
            "deploying": "🔄",
            "success": "🚀",
            "failed": "💥",
            "rollback": "↩️",
        }

        env_emojis = {
            "production": "🌍",
            "staging": "🎭",
            "development": "🔧",
            "testing": "🧪",
        }

        message = f"""
{status_emojis.get(status, "🔄")} **Deployment {status.title()}**

{env_emojis.get(environment, "🌐")} **Environment:** {environment}
📦 **Version:** `{version}`
⏰ **Time:** {datetime.now().strftime("%H:%M:%S")}
        """.strip()

        if status == "success":
            message += "\n\n✅ **Deployment completed successfully!**"
            buttons = [
                {"text": "🌐 View Live Site", "url": context.get("live_url", "#")},
                {"text": "📊 Monitor Health", "url": context.get("health_url", "#")},
                {"text": "📈 Analytics", "url": context.get("analytics_url", "#")},
            ]
        elif status == "failed":
            message += f"\n\n❌ **Deployment failed!**\n💬 **Error:** {context.get('error', 'Unknown error')}"
            buttons = [
                {"text": "🔄 Retry Deploy", "callback_data": "retry_deploy"},
                {"text": "↩️ Rollback", "callback_data": "rollback_deploy"},
                {"text": "🐛 View Logs", "url": context.get("logs_url", "#")},
            ]
        else:
            message += "\n\n🔄 **Deployment in progress...**"
            buttons = [
                {"text": "📊 Monitor Progress", "url": context.get("monitor_url", "#")},
                {"text": "🔍 View Logs", "url": context.get("logs_url", "#")},
            ]

        data = {
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(self.create_inline_keyboard(buttons)),
        }

        response = self.send_request("sendMessage", data)
        if response.get("ok"):
            return response["result"]["message_id"]
        return None


def main():
    """🎯 Main entry point for the notification system"""
    if len(sys.argv) < 2:
        return 1

    action = sys.argv[1]
    notifier = TelegramNotifier()

    # Read context from environment or file
    context = {}

    # GitHub Actions environment variables
    context.update(
        {
            "repository": os.getenv("GITHUB_REPOSITORY", "unknown/repo"),
            "branch": os.getenv("GITHUB_REF_NAME", "unknown"),
            "commit": os.getenv("GITHUB_SHA", "unknown"),
            "author": os.getenv("GITHUB_ACTOR", "unknown"),
            "workflow": os.getenv("GITHUB_WORKFLOW", "CI/CD"),
            "workflow_url": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}",
            "commit_url": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', '')}/commit/{os.getenv('GITHUB_SHA', '')}",
            "logs_url": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}",
        }
    )

    # Load additional context from file if provided
    context_file = os.getenv("TELEGRAM_CONTEXT_FILE")
    if context_file and os.path.exists(context_file):
        try:
            with open(context_file) as f:
                file_context = json.load(f)
                context.update(file_context)
        except (OSError, json.JSONDecodeError):
            pass

    # Handle different actions
    try:
        if action == "start":
            message_id = notifier.send_pipeline_start(context)
            if message_id:
                # Save message ID for later updates
                with open("/tmp/telegram_message_id", "w") as f:  # noqa: S108
                    f.write(str(message_id))

        elif action == "update":
            message_id_file = "/tmp/telegram_message_id"  # noqa: S108
            if os.path.exists(message_id_file):
                with open(message_id_file) as f:
                    message_id = int(f.read().strip())

                step = sys.argv[2] if len(sys.argv) > 2 else "Unknown step"
                progress = int(sys.argv[3]) if len(sys.argv) > 3 else 50
                status = sys.argv[4] if len(sys.argv) > 4 else "running"

                notifier.update_pipeline_progress(
                    message_id, step, progress, context, status
                )

        elif action == "success":
            message_id_file = "/tmp/telegram_message_id"  # noqa: S108
            if os.path.exists(message_id_file):
                with open(message_id_file) as f:
                    message_id = int(f.read().strip())

                print(  # noqa: T201
                    f"DEBUG: Sending success notification to message_id: {message_id}"
                )
                print(f"DEBUG: Context keys: {list(context.keys())}")  # noqa: T201
                print(f"DEBUG: Test summary: {context.get('test_summary')}")  # noqa: T201
                print(f"DEBUG: Coverage: {context.get('coverage')}")  # noqa: T201
                result = notifier.send_pipeline_success(message_id, context)
                print(f"DEBUG: Success notification result: {result}")  # noqa: T201

        elif action == "failure":
            message_id_file = "/tmp/telegram_message_id"  # noqa: S108
            if os.path.exists(message_id_file):
                with open(message_id_file) as f:
                    message_id = int(f.read().strip())

                notifier.send_pipeline_failure(message_id, context)

        elif action == "deploy":
            notifier.send_deployment_notification(context)

    except (ValueError, OSError, json.JSONDecodeError):
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
