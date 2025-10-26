#!/usr/bin/env python3
"""
macspace CLI - simple workspace manager for macOS.

Workspaces stored at: ~/.macspace/workspaces.json
Each workspace is a dict: {"name": <str>, "apps": [<app name strings>]}
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".macspace"
CONFIG_FILE = CONFIG_DIR / "workspaces.json"


def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump({"workspaces": []}, f)


def load_data():
    ensure_config()
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    ensure_config()
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_installed_apps():
    """
    Return a sorted list of app "display names" found in typical macOS app folders.
    We look in /Applications and ~/Applications, and pick the bundle names without suffix.
    """
    app_paths = [Path("/Applications"), Path.home() / "Applications"]
    apps = set()
    for p in app_paths:
        if p.exists():
            for entry in p.iterdir():
                if entry.suffix == ".app":
                    apps.add(entry.stem)
    # Additional: use mdfind to catch other app installs (spotlight)
    try:
        out = subprocess.check_output(
            ["mdfind", "kMDItemKind == 'Application'"], stderr=subprocess.DEVNULL
        ).decode("utf-8")
        for line in out.splitlines():
            path = Path(line)
            if path.suffix == ".app":
                apps.add(path.stem)
    except Exception:
        # mdfind may be slow or unavailable; ignore failures
        pass
    return sorted(apps, key=lambda s: s.lower())


def find_workspace(data, name):
    for w in data["workspaces"]:
        if w["name"] == name:
            return w
    return None


def cmd_create(args):
    data = load_data()
    if find_workspace(data, args.name):
        print(f"Workspace '{args.name}' already exists.")
        return
    ws = {"name": args.name, "apps": []}
    if args.apps:
        # apps passed as comma-separated
        input_apps = [a.strip() for a in args.apps.split(",") if a.strip()]
        ws["apps"] = input_apps
    data["workspaces"].append(ws)
    save_data(data)
    print(f"Created workspace '{args.name}'.")
    print("Installed apps detected on this Mac:")
    apps = get_installed_apps()
    if not apps:
        print("  (No apps found in /Applications or ~/Applications)")
    else:
        for a in apps:
            print(f"  - {a}")
    if ws["apps"]:
        print("\nAdded apps to workspace:")
        for a in ws["apps"]:
            print(f"  - {a}")


def cmd_list(args):
    data = load_data()
    if not data["workspaces"]:
        print("No workspaces. Create one with: macspace create NAME")
        return
    for w in data["workspaces"]:
        print(f"- {w['name']} ({len(w['apps'])} apps)")


def cmd_show(args):
    data = load_data()
    w = find_workspace(data, args.name)
    if not w:
        print(f"Workspace '{args.name}' not found.")
        return
    print(f"Workspace: {w['name']}")
    if not w["apps"]:
        print("  (no apps added)")
    else:
        for a in w["apps"]:
            print(f"  - {a}")


def cmd_delete(args):
    data = load_data()
    w = find_workspace(data, args.name)
    if not w:
        print(f"Workspace '{args.name}' not found.")
        return
    data["workspaces"].remove(w)
    save_data(data)
    print(f"Deleted workspace '{args.name}'.")


def cmd_add(args):
    data = load_data()
    w = find_workspace(data, args.name)
    if not w:
        print(f"Workspace '{args.name}' not found. Create it first.")
        return
    apps_to_add = [a.strip() for a in args.apps.split(",") if a.strip()]
    added = []
    for a in apps_to_add:
        if a not in w["apps"]:
            w["apps"].append(a)
            added.append(a)
    save_data(data)
    if added:
        print(f"Added: {', '.join(added)}")
    else:
        print("No new apps were added (they may already exist in workspace).")


def cmd_remove(args):
    data = load_data()
    w = find_workspace(data, args.name)
    if not w:
        print(f"Workspace '{args.name}' not found.")
        return
    apps_to_remove = [a.strip() for a in args.apps.split(",") if a.strip()]
    removed = []
    for a in apps_to_remove:
        if a in w["apps"]:
            w["apps"].remove(a)
            removed.append(a)
    save_data(data)
    if removed:
        print(f"Removed: {', '.join(removed)}")
    else:
        print("No matching apps found in workspace.")


def open_app(app_name):
    # Use macOS 'open -a "App Name"'
    try:
        subprocess.Popen(["open", "-a", app_name])
        return True
    except Exception:
        return False


def cmd_open(args):
    data = load_data()
    w = find_workspace(data, args.name)
    if not w:
        print(f"Workspace '{args.name}' not found.")
        return
    if not w["apps"]:
        print(f"Workspace '{args.name}' has no apps to open.")
        return
    print(f"Opening workspace '{w['name']}' apps...")
    installed = set(get_installed_apps())
    for app in w["apps"]:
        if app in installed:
            print(f"  Opening {app} ...")
            ok = open_app(app)
            if not ok:
                print(f"    Failed to open {app} (open command error).")
        else:
            # Still try to open — user might have app in different path / name
            print(f"  Attempting to open {app} (not found in standard locations)...")
            ok = open_app(app)
            if not ok:
                print(f"    Could not open {app}. Is the app name correct?")


def cmd_apps(args):
    apps = get_installed_apps()
    if not apps:
        print("No applications detected in /Applications or ~/Applications.")
        return
    print("Installed applications (sample):")
    for a in apps:
        print(f"  - {a}")


def build_parser():
    parser = argparse.ArgumentParser(prog="macspace", description="macspace - workspace manager for macOS")
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create a workspace")
    p_create.add_argument("name", help="Workspace name")
    p_create.add_argument("--apps", help="Comma-separated list of app names to add", default=None)
    p_create.set_defaults(func=cmd_create)

    p_list = sub.add_parser("list", help="List all workspaces")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show a workspace and its apps")
    p_show.add_argument("name", help="Workspace name")
    p_show.set_defaults(func=cmd_show)

    p_delete = sub.add_parser("delete", help="Delete a workspace")
    p_delete.add_argument("name", help="Workspace name")
    p_delete.set_defaults(func=cmd_delete)

    p_add = sub.add_parser("add", help="Add apps to a workspace")
    p_add.add_argument("name", help="Workspace name")
    p_add.add_argument("--apps", required=True, help="Comma-separated app names to add")
    p_add.set_defaults(func=cmd_add)

    p_remove = sub.add_parser("remove", help="Remove apps from a workspace")
    p_remove.add_argument("name", help="Workspace name")
    p_remove.add_argument("--apps", required=True, help="Comma-separated app names to remove")
    p_remove.set_defaults(func=cmd_remove)

    p_open = sub.add_parser("open", help="Open all apps in a workspace")
    p_open.add_argument("name", help="Workspace name")
    p_open.set_defaults(func=cmd_open)

    p_apps = sub.add_parser("apps", help="List installed macOS apps detected")
    p_apps.set_defaults(func=cmd_apps)

    return parser


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    if not argv:
        parser.print_help()
        return
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
