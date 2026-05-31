import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from problemnaire.config import load_config, save_config, Config, is_setup_complete, has_api_key, CONFIG_DIR
from problemnaire import progress as prog
from problemnaire import feedback as fb
from problemnaire import verifier
from problemnaire import claude_advisor
from problemnaire.fetchers.codeforces import fetch_cf_profile
from problemnaire.fetchers.leetcode import fetch_lc_profile
from problemnaire.fetchers.codechef import fetch_cc_profile
from problemnaire.analyzers.codeforces import analyze_cf
from problemnaire.analyzers.leetcode import analyze_lc
from problemnaire.analyzers.codechef import analyze_cc
from problemnaire.display.output import (
    print_header, print_cf_analysis, print_lc_analysis,
    print_cc_analysis, console,
)

app = typer.Typer(
    name="problemnaire",
    help="AI-powered competitive programming coach. Run 'setup' first.",
    add_completion=False,
)


# ── setup ──────────────────────────────────────────────────────────────────────

@app.command()
def setup():
    """First-time setup: API key, handles, and handle ownership verification."""
    print_header()
    console.print(Panel(
        "Welcome to Problemnaire!\nLet's set up your profile.",
        border_style="cyan",
    ))

    config = load_config()

    # API key
    console.print("\n[bold]Step 1: Anthropic API Key[/bold] [dim](optional)[/dim]")
    console.print("[dim]Enables AI-powered recommendations via Claude Haiku/Sonnet.[/dim]")
    console.print("[dim]Skip this to use the tool without AI (analysis, tracking, and verification still work).[/dim]")
    key = Prompt.ask(
        "API key (press Enter to skip)",
        default=config.api_key if config.api_key else "",
        password=True,
    )
    config.api_key = key.strip()

    # Handles
    console.print("\n[bold]Step 2: Your Handles[/bold]")
    console.print("[dim]Press Enter to skip a platform.[/dim]")
    cf  = Prompt.ask("Codeforces handle", default=config.handles.get("cf", ""))
    lc  = Prompt.ask("LeetCode username", default=config.handles.get("lc", ""))
    cc  = Prompt.ask("CodeChef username",  default=config.handles.get("cc", ""))

    config.handles = {k: v for k, v in {"cf": cf, "lc": lc, "cc": cc}.items() if v}
    if not config.verified:
        config.verified = {}

    save_config(config)

    # Verification
    console.print("\n[bold]Step 3: Handle Verification[/bold]")
    console.print("[dim]We verify you own each handle so your data stays accurate.[/dim]\n")

    if cf and not config.verified.get("cf"):
        _verify_cf(cf, config)

    if lc and not config.verified.get("lc"):
        _verify_lc(lc, config)

    if cc and not config.verified.get("cc"):
        _verify_cc(cc, config)

    save_config(config)
    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run [cyan]problemnaire analyze[/cyan] to get your first AI-powered study plan.")


def _verify_cf(handle: str, config: Config):
    console.print(f"[yellow]CF[/yellow] Verifying [bold]{handle}[/bold]...")
    if verifier.is_cf_handle_verified(handle):
        config.verified["cf"] = True
        console.print("[green]  Verified![/green] (found AC on problem 4A)")
        return
    console.print(
        f"  To prove ownership, solve [bold]CF 4A - Watermelon[/bold]:\n"
        f"  [cyan]{verifier.CF_VERIFY_URL}[/cyan]"
    )
    Prompt.ask("  Press Enter once you've submitted AC")
    if verifier.is_cf_handle_verified(handle):
        config.verified["cf"] = True
        console.print("[green]  Verified![/green]")
    else:
        console.print("[red]  Not verified yet.[/red] Run setup again after submitting.")


def _verify_lc(handle: str, config: Config):
    console.print(f"[blue]LC[/blue] Verifying [bold]{handle}[/bold]...")
    if verifier.is_lc_handle_verified(handle):
        config.verified["lc"] = True
        console.print("[green]  Verified![/green] (found AC on Two Sum)")
        return
    console.print(
        f"  To prove ownership, solve [bold]LC - Two Sum[/bold]:\n"
        f"  [cyan]{verifier.LC_VERIFY_URL}[/cyan]"
    )
    Prompt.ask("  Press Enter once you've submitted AC")
    if verifier.is_lc_handle_verified(handle):
        config.verified["lc"] = True
        console.print("[green]  Verified![/green]")
    else:
        console.print("[red]  Not verified yet.[/red] Run setup again after submitting.")


def _verify_cc(handle: str, config: Config):
    console.print(f"[magenta]CC[/magenta] Verifying [bold]{handle}[/bold]...")
    if verifier.is_cc_handle_reachable(handle):
        config.verified["cc"] = True
        console.print("[green]  Profile found.[/green] (CodeChef has no public submissions API)")
    else:
        console.print("[red]  Could not reach profile.[/red] Check the handle spelling.")


# ── analyze ────────────────────────────────────────────────────────────────────

@app.command()
def analyze(
    boost: int = typer.Option(200, "--boost", "-b", help="Target CF rating boost"),
):
    """
    Fetch your profiles, check pending problems, get AI recommendations,
    and update your progress log.
    """
    config = load_config()
    if not is_setup_complete(config):
        console.print("[red]Run 'problemnaire setup' first.[/red]")
        raise typer.Exit(1)

    print_header()
    data = prog.load()

    # ── 1. Check pending problems from last session ────────────────────────────
    pending = data.get("pending_problems", [])
    newly_solved: list[str] = []

    if pending:
        console.rule("[bold]Checking last session's problems[/bold]")
        console.print()
        cf_handle = config.handles.get("cf", "")
        lc_handle = config.handles.get("lc", "")

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console) as p:
            t = p.add_task("Verifying via API...", total=None)
            for problem in pending:
                since = problem.get("assigned_date", "2000-01-01")
                if problem["platform"] == "cf" and cf_handle:
                    cid, idx = problem["id"].split("-")
                    solved = verifier.is_cf_problem_solved(cf_handle, cid, idx, since)
                elif problem["platform"] == "lc" and lc_handle:
                    solved = verifier.is_lc_problem_solved(lc_handle, problem["id"], since)
                else:
                    solved = False
                if solved:
                    newly_solved.append(problem["id"])
            p.remove_task(t)

        _show_pending_status(pending, newly_solved)

    # ── 2. Per-problem feedback + overall session feedback ─────────────────────
    feedback = ""
    feedback_entries: list[dict] = []

    if pending:
        console.print()
        solved_problems = [p for p in pending if p["id"] in newly_solved]
        if solved_problems:
            console.print("[bold]Quick feedback on each solved problem:[/bold]")
            console.print("[dim]This builds your revision sheet and helps Claude improve recommendations.[/dim]")
            for problem in solved_problems:
                entry = _collect_problem_feedback(problem)
                if entry:
                    feedback_entries.append(entry)

        console.print()
        console.print("[bold]Overall session feedback:[/bold]")
        console.print("[dim]What was challenging? Any topics that clicked or confused you?[/dim]")
        feedback = Prompt.ask("Your feedback (or Enter to skip)", default="")
        console.print()

    # ── 3. Fetch fresh profile data ───────────────────────────────────────────
    console.rule("[bold]Fetching your profiles[/bold]")
    console.print()

    cf_analysis = lc_analysis = cc_analysis = None
    cf_rating = lc_solved = cc_rating = 0

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console) as p:

        if config.handles.get("cf"):
            handle = config.handles["cf"]
            if not config.verified.get("cf"):
                console.print(f"[yellow]CF handle '{handle}' not verified. Run setup.[/yellow]")
            else:
                t = p.add_task(f"Fetching Codeforces ({handle})...", total=None)
                try:
                    cf_profile = fetch_cf_profile(handle)
                    cf_analysis = analyze_cf(cf_profile, rating_boost=boost)
                    cf_rating = cf_analysis.current_rating
                except Exception as e:
                    console.print(f"[red]CF error:[/red] {e}")
                finally:
                    p.remove_task(t)

        if config.handles.get("lc"):
            handle = config.handles["lc"]
            if not config.verified.get("lc"):
                console.print(f"[yellow]LC handle '{handle}' not verified. Run setup.[/yellow]")
            else:
                t = p.add_task(f"Fetching LeetCode ({handle})...", total=None)
                try:
                    lc_profile = fetch_lc_profile(handle)
                    lc_analysis = analyze_lc(lc_profile)
                    lc_solved = lc_analysis.total_solved
                except Exception as e:
                    console.print(f"[red]LC error:[/red] {e}")
                finally:
                    p.remove_task(t)

        if config.handles.get("cc"):
            handle = config.handles["cc"]
            t = p.add_task(f"Fetching CodeChef ({handle})...", total=None)
            try:
                cc_profile = fetch_cc_profile(handle)
                cc_analysis = analyze_cc(cc_profile)
                cc_rating = cc_analysis.current_rating
            except Exception as e:
                console.print(f"[red]CC error:[/red] {e}")
            finally:
                p.remove_task(t)

    # ── 4. Display platform analysis ──────────────────────────────────────────
    if cf_analysis:
        print_cf_analysis(cf_analysis)
    if lc_analysis:
        print_lc_analysis(lc_analysis)
    if cc_analysis:
        print_cc_analysis(cc_analysis)

    # ── 5. Ask Claude for personalised recommendations (optional) ─────────────
    assigned_problems: list[dict] = []
    session_summary = ""

    if not has_api_key(config):
        console.rule("[bold dim]AI Recommendations[/bold dim]")
        console.print(Panel(
            "No Anthropic API key configured.\n\n"
            "To get AI-powered problem recommendations, run [cyan]problemnaire setup[/cyan]\n"
            "and enter an API key. Get one free at [cyan]https://console.anthropic.com[/cyan]\n\n"
            "Everything else (analysis, tracking, verification, feedback sheet) works without it.",
            border_style="dim",
            title="[dim]Claude Recommendations Skipped[/dim]",
        ))
    else:
        console.rule("[bold cyan]Claude's Recommendations[/bold cyan]")
        console.print()

        last_summary  = data.get("last_session_summary", "")
        last_feedback = data["sessions"][-1].get("feedback", "") if data.get("sessions") else ""

        recs = None
        with Progress(SpinnerColumn(), TextColumn("Asking Claude..."), transient=True, console=console) as p:
            t = p.add_task("", total=None)
            try:
                recs = claude_advisor.get_recommendations(
                    cf_analysis=cf_analysis,
                    lc_analysis=lc_analysis,
                    cc_analysis=cc_analysis,
                    last_summary=last_summary,
                    last_feedback=last_feedback,
                    api_key=config.api_key,
                )
            except Exception as e:
                console.print(f"[red]Claude error:[/red] {e}")
            finally:
                p.remove_task(t)

        if recs:
            _show_recommendations(recs, assigned_problems)

        # Build compact session summary for next run
        if recs:
            solved_titles = [p["title"] for p in pending if p["id"] in newly_solved]
            try:
                session_summary = claude_advisor.build_session_summary(
                    feedback=feedback,
                    problems_solved=solved_titles,
                    api_key=config.api_key,
                )
            except Exception:
                session_summary = recs.get("session_summary", "")

    # ── 7. Persist progress + feedback sheet ──────────────────────────────────
    prog.add_session(
        data,
        cf_rating=cf_rating,
        lc_solved=lc_solved,
        cc_rating=cc_rating,
        problems_assigned=assigned_problems,
        problems_solved=newly_solved,
        feedback=feedback,
        summary=session_summary,
    )
    prog.save(data)

    if feedback_entries:
        sheet = fb.load()
        for entry in feedback_entries:
            fb.add_entry(sheet, entry)
        fb.save(sheet)
        sheet_md  = CONFIG_DIR / "feedback_sheet.md"
        sheet_csv = CONFIG_DIR / "feedback_sheet.csv"
        console.print(f"[dim]Feedback sheet -> {sheet_md}[/dim]")
        console.print(f"[dim]               -> {sheet_csv} (Excel)[/dim]")

    report_path = CONFIG_DIR / "progress.md"
    console.print(f"[dim]Progress saved -> {report_path}[/dim]")


# ── review ─────────────────────────────────────────────────────────────────────

@app.command()
def review(
    period: str = typer.Option("month", "--period", "-p", help="month | quarter | all"),
):
    """
    Deep AI analysis of your problem-solving patterns using your feedback sheet.

    WARNING: feeds your full feedback history to Claude Sonnet — significantly
    more tokens than a regular analyze. Use for monthly reviews, not daily.
    """
    config = load_config()
    if not is_setup_complete(config):
        console.print("[red]Run 'problemnaire setup' first.[/red]")
        raise typer.Exit(1)

    if not has_api_key(config):
        console.print(Panel(
            "The [bold]review[/bold] command requires an Anthropic API key to call Claude Sonnet.\n\n"
            "Run [cyan]problemnaire setup[/cyan] and enter your API key to enable it.\n"
            "Get one at [cyan]https://console.anthropic.com[/cyan]",
            title="[yellow]API Key Required[/yellow]",
            border_style="yellow",
        ))
        raise typer.Exit(0)

    print_header()

    console.print(Panel(
        "[bold yellow]Token Warning[/bold yellow]\n\n"
        "This command feeds your complete problem feedback sheet to Claude Sonnet\n"
        "(a higher-quality, higher-cost model than the one used in 'analyze').\n\n"
        "It will use significantly more tokens. Best used for monthly reviews,\n"
        "not after every session.\n\n"
        f"Period: [bold]{period}[/bold]",
        border_style="yellow",
    ))

    if not Confirm.ask("Continue?", default=True):
        raise typer.Exit(0)

    sheet = fb.load()
    entries = fb.filter_by_period(sheet, period)

    if not entries:
        console.print(f"\n[yellow]No feedback entries found for period '{period}'.[/yellow]")
        console.print("[dim]Solve some Claude-assigned problems first — feedback is collected per solve.[/dim]")
        raise typer.Exit(0)

    period_label = {"month": "this month", "quarter": "this quarter", "all": "all time"}.get(period, period)
    console.print(f"\nSending [bold]{len(entries)}[/bold] problem entries ({period_label}) to Claude Sonnet...\n")

    feedback_md = fb.to_markdown_content(entries)

    analysis = ""
    with Progress(SpinnerColumn(), TextColumn("Claude is reading your feedback sheet..."), transient=True, console=console) as p:
        t = p.add_task("", total=None)
        try:
            analysis = claude_advisor.deep_analysis(
                feedback_md=feedback_md,
                period=period,
                api_key=config.api_key,
            )
        except Exception as e:
            console.print(f"[red]Claude error:[/red] {e}")
        finally:
            p.remove_task(t)

    if analysis:
        console.print(Panel(
            analysis,
            title=f"[bold cyan]Deep Analysis — {period_label.title()}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))
        sheet_path = CONFIG_DIR / "feedback_sheet.md"
        console.print(f"\n[dim]Full feedback sheet -> {sheet_path}[/dim]")


# ── feedback ───────────────────────────────────────────────────────────────────

@app.command(name="feedback")
def add_feedback():
    """
    Record a freeform progress note any time — after a contest, a study session,
    or whenever something clicks or confuses you. Saved instantly to progress.md.
    """
    config = load_config()
    if not is_setup_complete(config):
        console.print("[red]Run 'problemnaire setup' first.[/red]")
        raise typer.Exit(1)

    print_header()
    console.print(Panel(
        "Record a quick progress note.\n"
        "[dim]This is saved immediately to your progress.md — use it after any study session,\n"
        "contest, or whenever something clicks or confuses you.[/dim]",
        border_style="cyan",
        title="[bold cyan]Progress Feedback[/bold cyan]",
    ))
    console.print()

    mood = Prompt.ask(
        "How are you feeling about your prep?",
        choices=["Great", "Good", "Okay", "Struggling"],
        default="Good",
    )
    worked_on = Prompt.ask(
        "What did you work on today?",
        default="",
    )
    what_clicked = Prompt.ask(
        "What clicked / what did you understand better?",
        default="",
    )
    what_confused = Prompt.ask(
        "What confused you or felt hard?",
        default="",
    )
    next_goal = Prompt.ask(
        "Goal for next session?",
        default="",
    )

    if not any([worked_on, what_clicked, what_confused, next_goal]):
        console.print("[yellow]Nothing entered — feedback not saved.[/yellow]")
        raise typer.Exit(0)

    data = prog.load()
    prog.add_feedback_entry(
        data,
        mood=mood,
        worked_on=worked_on,
        what_clicked=what_clicked,
        what_confused=what_confused,
        next_goal=next_goal,
    )
    prog.save(data)

    console.print()
    console.print("[bold green]Feedback saved![/bold green]")
    console.print(f"[dim]-> {CONFIG_DIR / 'progress.md'}[/dim]")


# ── progress ───────────────────────────────────────────────────────────────────

@app.command(name="progress")
def show_progress():
    """Show pending problems and recent session history."""
    print_header()
    data = prog.load()

    pending = data.get("pending_problems", [])
    console.rule("[bold]Pending Problems[/bold]")
    if not pending:
        console.print("[dim]No pending problems. Run 'analyze' to get new ones.[/dim]")
    else:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Platform", style="cyan", justify="center")
        table.add_column("Problem")
        table.add_column("Tag", style="dim")
        table.add_column("Assigned", style="dim", justify="right")
        for p in pending:
            table.add_row(p["platform"].upper(), p["title"], p["tag"], p["assigned_date"])
        console.print(table)

    sessions = data.get("sessions", [])
    if sessions:
        console.print()
        console.rule("[bold]Recent Sessions[/bold]")
        for s in reversed(sessions[-3:]):
            solved = ", ".join(s["problems_solved"]) if s.get("problems_solved") else "none"
            console.print(
                f"[bold]{s['date']}[/bold]  CF={s['cf_rating']}  "
                f"LC={s['lc_solved']}  CC={s['cc_rating']}  "
                f"Solved: {solved}"
            )
            if s.get("feedback"):
                console.print(f"  Feedback: [italic]{s['feedback']}[/italic]")


# ── version ────────────────────────────────────────────────────────────────────

@app.command()
def version():
    """Show version."""
    console.print("[cyan]problemnaire[/cyan] v0.1.0")


# ── helpers ────────────────────────────────────────────────────────────────────

def _collect_problem_feedback(problem: dict) -> dict | None:
    """Ask the user quick feedback on a single solved problem."""
    from datetime import date as _date
    console.print(f"\n  [bold]{problem['title']}[/bold] ({problem['platform'].upper()} | {problem.get('tag', '')})")
    felt = Prompt.ask(
        "  How hard did it feel?",
        choices=["Easy", "Medium", "Hard", "Very Hard"],
        default="Medium",
    )
    hint  = Confirm.ask("  Did you need a hint or editorial?", default=False)
    notes = Prompt.ask("  Notes — what you learned / what tripped you up (Enter to skip)", default="")
    return {
        "date_solved"    : str(_date.today()),
        "platform"       : problem["platform"],
        "problem_id"     : problem["id"],
        "title"          : problem["title"],
        "tag"            : problem.get("tag", ""),
        "url"            : problem.get("url", ""),
        "assigned_date"  : problem.get("assigned_date", ""),
        "difficulty_felt": felt,
        "needed_hint"    : hint,
        "notes"          : notes,
    }


def _show_pending_status(pending: list, newly_solved: list[str]):
    table = Table(title="Pending Problems Status", box=box.SIMPLE_HEAVY)
    table.add_column("Platform", justify="center")
    table.add_column("Problem")
    table.add_column("Tag", style="dim")
    table.add_column("Status", justify="center")
    for p in pending:
        if p["id"] in newly_solved:
            status = "[green]SOLVED[/green]"
        else:
            status = "[yellow]Pending[/yellow]"
        table.add_row(p["platform"].upper(), p["title"], p["tag"], status)
    console.print(table)


def _show_recommendations(recs: dict, assigned_problems: list):
    if recs.get("advice"):
        console.print(Panel(recs["advice"], title="[bold cyan]Personalised Advice[/bold cyan]", border_style="cyan"))
        console.print()

    cf_probs = recs.get("cf_problems", [])
    lc_probs = recs.get("lc_problems", [])

    if cf_probs:
        table = Table(title="Codeforces Problems to Solve", box=box.SIMPLE_HEAVY)
        table.add_column("Problem", style="cyan")
        table.add_column("Rating", justify="center")
        table.add_column("Why", style="dim")
        table.add_column("URL")
        for p in cf_probs:
            cid  = str(p.get("contest_id", ""))
            idx  = str(p.get("index", ""))
            url  = f"https://codeforces.com/problemset/problem/{cid}/{idx}"
            pid  = f"{cid}-{idx}"
            table.add_row(p.get("title", pid), str(p.get("rating", "")), p.get("reason", ""), url)
            assigned_problems.append({
                "platform": "cf",
                "id": pid,
                "title": p.get("title", pid),
                "tag": p.get("reason", ""),
                "url": url,
            })
        console.print(table)

    if lc_probs:
        table = Table(title="LeetCode Problems to Solve", box=box.SIMPLE_HEAVY)
        table.add_column("Problem", style="blue")
        table.add_column("Difficulty", justify="center")
        table.add_column("Why", style="dim")
        table.add_column("URL")
        for p in lc_probs:
            slug = p.get("slug", "")
            url  = f"https://leetcode.com/problems/{slug}/"
            table.add_row(p.get("title", slug), p.get("difficulty", ""), p.get("reason", ""), url)
            assigned_problems.append({
                "platform": "lc",
                "id": slug,
                "title": p.get("title", slug),
                "tag": p.get("reason", ""),
                "url": url,
            })
        console.print(table)


if __name__ == "__main__":
    app()
