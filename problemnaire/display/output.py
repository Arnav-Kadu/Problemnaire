from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from problemnaire.analyzers.codeforces import CFAnalysis
from problemnaire.analyzers.leetcode import LCAnalysis
from problemnaire.analyzers.codechef import CCAnalysis


console = Console(highlight=False)


def print_header():
    console.print(Panel.fit(
        "[bold cyan]PROBLEMNAIRE[/bold cyan]\n"
        "[dim]Competitive Programming Profile Analyzer[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def print_cf_analysis(analysis: CFAnalysis):
    console.rule("[bold yellow]Codeforces Analysis[/bold yellow]")
    console.print()

    rating_color = _cf_rating_color(analysis.current_rating)
    target_color = _cf_rating_color(analysis.target_rating)
    console.print(Panel(
        f"Handle: [bold]{analysis.handle}[/bold]\n"
        f"Current Rating: [{rating_color}]{analysis.current_rating}[/{rating_color}]\n"
        f"Target Rating:  [{target_color}]{analysis.target_rating}[/{target_color}]  "
        f"[dim](+{analysis.target_rating - analysis.current_rating})[/dim]\n"
        f"Total Solved:   [bold]{analysis.total_solved}[/bold] "
        f"[dim]({analysis.rated_solved} rated)[/dim]",
        title="[bold yellow]Profile[/bold yellow]",
        border_style="yellow",
    ))

    if analysis.solved_by_rating:
        table = Table(title="Problems Solved by Difficulty", box=box.SIMPLE_HEAVY, show_header=True)
        table.add_column("Rating", style="cyan", justify="center")
        table.add_column("Count", justify="right")
        table.add_column("Bar", min_width=20)

        max_count = max(analysis.solved_by_rating.values(), default=1)
        for band, count in sorted(analysis.solved_by_rating.items(), key=lambda x: int(x[0].rstrip("+"))):
            bar_len = int((count / max_count) * 20)
            bar = "[green]" + "#" * bar_len + "[/green]" + "-" * (20 - bar_len)
            table.add_row(band, str(count), bar)
        console.print(table)

    if analysis.tag_stats:
        table = Table(
            title=f"Key Tags for Target Rating {analysis.target_rating}",
            box=box.SIMPLE_HEAVY,
        )
        table.add_column("Tag", style="cyan")
        table.add_column("Total Solved", justify="right")
        table.add_column("In Target Range", justify="right")
        table.add_column("Status", justify="center")

        for ts in sorted(analysis.tag_stats, key=lambda x: x.total_solved):
            status = (
                "[red]Weak - Practice needed[/red]" if ts.tag in analysis.weak_tags
                else "[green]OK[/green]"
            )
            table.add_row(ts.tag, str(ts.total_solved), str(ts.solved_at_target), status)
        console.print(table)

    if analysis.weak_tags:
        console.print(Panel(
            _cf_recommendations(analysis),
            title="[bold red]Action Plan to +200 Rating[/bold red]",
            border_style="red",
        ))
    else:
        console.print("[green]All key tags look solid! Focus on contest practice and upsolving.[/green]")

    console.print()


def print_lc_analysis(analysis: LCAnalysis):
    console.rule("[bold blue]LeetCode Analysis[/bold blue]")
    console.print()

    easy_pct = _pct(analysis.easy_solved, analysis.total_solved)
    med_pct = _pct(analysis.medium_solved, analysis.total_solved)
    hard_pct = _pct(analysis.hard_solved, analysis.total_solved)

    console.print(Panel(
        f"Username: [bold]{analysis.username}[/bold]\n"
        f"Easy:     [green]{analysis.easy_solved}[/green]   ({easy_pct}%)\n"
        f"Medium:   [yellow]{analysis.medium_solved}[/yellow]  ({med_pct}%)\n"
        f"Hard:     [red]{analysis.hard_solved}[/red]   ({hard_pct}%)\n"
        f"Total:    [bold]{analysis.total_solved}[/bold]\n\n"
        f"Assessment: [italic]{analysis.difficulty_score}[/italic]",
        title="[bold blue]Profile[/bold blue]",
        border_style="blue",
    ))

    if analysis.top_topics:
        table = Table(title="Strongest Topics", box=box.SIMPLE_HEAVY)
        table.add_column("Topic", style="cyan")
        table.add_column("Solved", justify="right")
        for topic, count in analysis.top_topics:
            table.add_row(topic, str(count))
        console.print(table)

    if analysis.weak_topics:
        console.print(Panel(
            _lc_recommendations(analysis),
            title="[bold red]Topics to Improve (< 10 solved)[/bold red]",
            border_style="red",
        ))

    console.print()


def print_cc_analysis(analysis: CCAnalysis):
    console.rule("[bold magenta]CodeChef Analysis[/bold magenta]")
    console.print()

    console.print(Panel(
        f"Username:       [bold]{analysis.username}[/bold]\n"
        f"Current Rating: [bold magenta]{analysis.current_rating}[/bold magenta] "
        f"[dim]({analysis.current_band})[/dim]\n"
        f"Highest Rating: [bold]{analysis.highest_rating}[/bold]\n"
        f"Next Tier:      [cyan]{analysis.next_band}[/cyan]  "
        f"[dim]+{analysis.points_to_next} points needed[/dim]\n"
        f"Problems Solved: {analysis.fully_solved}\n\n"
        f"Advice: [italic]{analysis.advice}[/italic]",
        title="[bold magenta]Profile[/bold magenta]",
        border_style="magenta",
    ))
    console.print()


def print_global_summary(cf: "CFAnalysis | None", lc: "LCAnalysis | None", cc: "CCAnalysis | None"):
    console.rule("[bold white]Overall Study Plan[/bold white]")
    console.print()

    lines = []

    if cf and cf.weak_tags:
        lines.append(f"[yellow]CF[/yellow]  Weak areas: {', '.join(cf.weak_tags[:4])}")
        lines.append(f"     -> Solve 10+ problems per weak tag at rating {cf.current_rating}-{cf.target_rating}")
        lines.append(f"     -> Upsolve past contest problems in those tags")

    if lc:
        if lc.weak_topics:
            names = ', '.join(t for t, _ in lc.weak_topics[:3])
            lines.append(f"[blue]LC[/blue]  Weak topics (per platform tags): {names}")
        lines.append(f"     -> Solve 10+ problems per weak topic")

    if cc and cc.points_to_next > 0:
        lines.append(f"[magenta]CC[/magenta]  Need +{cc.points_to_next} rating -> {cc.next_band}")
        lines.append(f"     -> {cc.advice}")

    if lines:
        console.print(Panel(
            "\n".join(lines),
            title="[bold white]Prioritized Recommendations[/bold white]",
            border_style="white",
            padding=(1, 2),
        ))
    else:
        console.print("[bold green]Looking solid across all platforms! Keep grinding contests.[/bold green]")

    console.print()


def _cf_rating_color(rating: int) -> str:
    if rating < 1200:
        return "white"
    if rating < 1400:
        return "green"
    if rating < 1600:
        return "cyan"
    if rating < 1900:
        return "blue"
    if rating < 2100:
        return "magenta"
    if rating < 2400:
        return "yellow"
    return "red"


def _cf_recommendations(a: CFAnalysis) -> str:
    lines = [
        f"To go from [bold]{a.current_rating}[/bold] -> [bold]{a.target_rating}[/bold], "
        f"prioritize these topics:\n"
    ]
    for tag in a.weak_tags:
        lines.append(f"  - [cyan]{tag}[/cyan]: solve 10+ problems at rating {a.current_rating}-{a.target_rating}")
    lines.append("")
    lines.append("[dim]Tip: Use Codeforces problemset filtered by tag + rating range.[/dim]")
    lines.append("[dim]Tip: Upsolve problems from Div 2 B/C that match your weak tags.[/dim]")
    return "\n".join(lines)


def _lc_recommendations(a: LCAnalysis) -> str:
    lines = ["Need more practice (solved fewer than 10):"]
    for tag, count in a.weak_topics[:10]:
        lines.append(f"  - [yellow]{tag}[/yellow]  ({count} solved)")
    lines.append("\n[dim]Tip: Pick a topic, solve 5 Easy + 10 Medium problems, then revisit.[/dim]")
    return "\n".join(lines)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0"
    return f"{part * 100 // total}"
