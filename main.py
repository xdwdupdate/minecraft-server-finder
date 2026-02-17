import socket
import os
import re
from mcstatus import JavaServer
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

console = Console()

def load_ascii():
    if os.path.exists('ascii.txt'):
        try:
            with open('ascii.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except: pass
    return "⚡ MC DISCOVERY ⚡"

def clean_motd(motd):
    if isinstance(motd, dict): motd = motd.get('text', '')
    clean = re.sub(r'§[0-9a-fk-orx]', '', str(motd))
    return clean.replace('\n', ' ').strip()[:40]

def get_ping_style(ping_str):
    ms = int(ping_str.replace('ms', ''))
    if ms < 50: return "bold green"
    if ms < 150: return "bold yellow"
    return "bold red"

def check_server(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25) 
            if s.connect_ex((ip, port)) == 0:
                server = JavaServer.lookup(f"{ip}:{port}")
                status = server.status()
                return {
                    "ip": f"{ip}:{port}",
                    "ver": str(status.version.name)[:12],
                    "players": f"{status.players.online}/{status.players.max}",
                    "motd": clean_motd(status.description) or "No description",
                    "ping": f"{int(status.latency)}ms",
                    "time": datetime.now().strftime("%H:%M:%S")
                }
    except: pass
    return None

def main():
    art = load_ascii()
    if not os.path.exists('ips.txt'):
        console.print("[bold red]❌ Файл ips.txt не найден![/bold red]")
        return

    with open('ips.txt', 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    found_count = 0
    total_scanned = 0
    ports = range(1, 65536)

    table = Table(expand=True, border_style="bright_blue", box=None)
    table.add_column("🕒 Время", style="dim white", width=10)
    table.add_column("🌐 IP:Порт", style="bold cyan", width=20)
    table.add_column("📝 MOTD (Описание)", style="italic white")
    table.add_column("🛠 Версия", style="magenta")
    table.add_column("👥 Игроки", style="bold yellow")
    table.add_column("📶 Пинг", justify="right")

    progress = Progress(
        SpinnerColumn("bouncingBar", style="bold magenta"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=None, style="bright_black", complete_style="bold cyan"),
        TextColumn("[bold cyan]{task.percentage:>3.0f}%"),
        TimeRemainingColumn()
    )

    def update_layout():
        layout = Layout()
        layout.split_column(
            Layout(Panel(art, style="bold cyan", border_style="magenta"), size=10),
            Layout(name="main", ratio=1)
        )
        layout["main"].split_row(
            Layout(Panel(progress, title="🚀 Progress", border_style="bright_black"), ratio=1),
            Layout(Panel(table, title="💎 Live Findings", border_style="bold green"), ratio=3)
        )
        return layout

    with Live(update_layout(), refresh_per_second=4, screen=True) as live:
        with ThreadPoolExecutor(max_workers=200) as executor:
            for ip in ips:
                task_id = progress.add_task(f"Scanning {ip}", total=len(ports))
                futures = {executor.submit(check_server, ip, port): port for port in ports}

                for future in as_completed(futures):
                    result = future.result()
                    total_scanned += 1
                    if result:
                        found_count += 1
                        ping_val = result["ping"]
                        table.add_row(
                            result["time"],
                            result["ip"],
                            result["motd"],
                            result["ver"],
                            result["players"],
                            f"[{get_ping_style(ping_val)}]{ping_val}[/]"
                        )
                        with open("found.txt", "a", encoding="utf-8") as f:
                            f.write(f"[{result['time']}] {result['ip']} | {result['ver']} | {result['motd']}\n")

                    progress.update(task_id, advance=1)
                progress.remove_task(task_id)

    console.clear()
    console.print(Panel(f"[bold green]✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО![/bold green]\n\n[white]Всего проверено портов: [bold]{total_scanned}[/]\nНайдено серверов: [bold cyan]{found_count}[/]\nРезультаты сохранены в: [bold underline]found.txt[/]", border_style="green", padding=(1, 2)))

if __name__ == "__main__":
    main()
