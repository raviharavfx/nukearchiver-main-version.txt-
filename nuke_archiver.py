# coding: utf-8
"""
==============================================================================
NukeArchiver  -  Node & Material Collection Tool for Nuke
==============================================================================
Version      : 1.1.0
Author       : Ravihara Perera
Copyright    : (c) 2025 Ravihara Perera. All Rights Reserved.
License      : Commercial License - Single User
Contact      : ravihara.perera@email.com

------------------------------------------------------------------------------
IMPORTANT - PLEASE READ BEFORE USE
------------------------------------------------------------------------------
This software is proprietary and confidential. It is licensed, not sold.
By using this software you agree to the following terms:

  1. SINGLE USER LICENSE
     This license grants ONE individual the right to install and use
     NukeArchiver on up to 2 personal workstations.

  2. NO REDISTRIBUTION
     You may NOT share, resell, sublicense, upload, or distribute this
     software or any part of it in any form, modified or unmodified,
     free of charge or for payment.

  3. NO MODIFICATION
     You may NOT decompile, reverse-engineer, disassemble, modify, or
     create derivative works based on this software.

  4. NO TRANSFER
     This license is non-transferable. It may not be assigned to another
     individual or organization.

  5. STUDIO / TEAM USE
     For studio or team licensing (multiple seats), please contact the
     author directly.

Unauthorized use, copying, or distribution of this software is a violation
of copyright law and may result in legal action.

------------------------------------------------------------------------------
DESCRIPTION
------------------------------------------------------------------------------
NukeArchiver collects selected nodes and all their connected compositing
materials (EXR sequences, footage, LUTs, 3D scenes, audio, and more)
into a clean, portable archive folder. The saved Nuke script is
automatically relinked to the new archive paths.

Features:
  - Archive selected nodes + all connected upstream/downstream nodes
  - Per Read-node subfolders inside footage/
  - Automatic path relinking in the archived .nk file
  - Image sequence handling with frame range support
  - UNC / network path support
  - JSON manifest log
  - Optional ZIP of entire archive
  - PySide2/PySide6 compatible UI

Compatible Nuke versions: 13, 14, 15
Platform: Windows, macOS, Linux

------------------------------------------------------------------------------
INSTALLATION
------------------------------------------------------------------------------
See README.txt included in this package for full installation instructions.
==============================================================================
"""

import os
import re
import sys
import json
import glob
import shutil
import zipfile
import datetime
import traceback
import tempfile
import urllib.request
import urllib.error

import nuke
import nukescripts

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Qt, QThread, Signal
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Qt, QThread, Signal

# ---------------------------------------------
# CONSTANTS
# ---------------------------------------------

VERSION = "1.1.0"
UPDATE_URL = "https://raw.githubusercontent.com/raviharavfx/nukearchiver-main-version.txt-/main/version.txt"

FILE_KNOBS = [
    "file", "proxy", "lut", "vfield_file", "cdl_file",
    "scene", "geo", "filename", "font", "audio",
    "ICC_in_profile", "ICC_out_profile", "icc_profile",
    "hiero_source", "manifest", "input_file"
]

DARK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
QMainWindow, QDialog { background-color: #1a1a1a; }
QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: bold;
    color: #e0a040;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #4a4a4a;
    border-radius: 3px;
    padding: 6px 14px;
    color: #d4d4d4;
    min-width: 80px;
}
QPushButton:hover { background-color: #3a3a3a; border-color: #e0a040; color: #e0a040; }
QPushButton:pressed { background-color: #e0a040; color: #1a1a1a; }
QPushButton:disabled { background-color: #252525; color: #555; border-color: #333; }
QPushButton#archiveBtn {
    background-color: #c47d00;
    color: #1a1a1a;
    font-weight: bold;
    border: none;
    padding: 8px 20px;
    font-size: 13px;
}
QPushButton#archiveBtn:hover { background-color: #e0a040; }
QPushButton#archiveBtn:disabled { background-color: #3a3200; color: #666; }
QLineEdit {
    background-color: #252525;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 4px 8px;
    color: #d4d4d4;
}
QLineEdit:focus { border-color: #e0a040; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #4a4a4a;
    border-radius: 2px;
    background-color: #252525;
}
QCheckBox::indicator:checked { background-color: #e0a040; border-color: #e0a040; }
QProgressBar {
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    background-color: #252525;
    text-align: center;
    color: #d4d4d4;
    height: 18px;
}
QProgressBar::chunk { background-color: #e0a040; border-radius: 2px; }
QTextEdit {
    background-color: #141414;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    color: #a0a0a0;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 4px;
}
QLabel#titleLabel { font-size: 16px; font-weight: bold; color: #e0a040; letter-spacing: 2px; }
QLabel#subtitleLabel { font-size: 10px; color: #666; letter-spacing: 1px; }
QLabel#creatorLabel { font-size: 10px; color: #c47d00; letter-spacing: 1px; font-style: italic; }
QScrollBar:vertical { background: #1e1e1e; width: 8px; }
QScrollBar::handle:vertical { background: #3a3a3a; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #e0a040; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: #1e1e1e; height: 8px; }
QScrollBar::handle:horizontal { background: #3a3a3a; border-radius: 4px; min-width: 20px; }
QLabel#copyrightLabel { font-size: 10px; color: #444; letter-spacing: 1px; }
QPushButton#updateBtn {
    background-color: #1e1e1e;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 4px 10px;
    color: #666;
    font-size: 10px;
}
QPushButton#updateBtn:hover { border-color: #e0a040; color: #e0a040; }
"""

# ---------------------------------------------
# HELPERS
# ---------------------------------------------

def resolve_sequence_path(path):
    glob_path = re.sub(r'#+', '*', path)
    glob_path = re.sub(r'%\d*d', '*', glob_path)
    is_sequence = glob_path != path
    return glob_path, is_sequence


def get_frame_range_files(path, first_frame=None, last_frame=None):
    glob_pattern, is_sequence = resolve_sequence_path(path)
    if not is_sequence:
        return [path] if os.path.exists(path) else []
    all_files = sorted(glob.glob(glob_pattern))
    if not all_files:
        return []
    if first_frame is None or last_frame is None:
        return all_files
    filtered = []
    for f in all_files:
        match = re.search(r'(\d+)(?=\.\w+$)', f)
        if match:
            frame_num = int(match.group(1))
            if first_frame <= frame_num <= last_frame:
                filtered.append(f)
        else:
            filtered.append(f)
    return filtered


def get_node_file_info(node):
    results = {}
    script_dir = os.path.dirname(nuke.root().name()) if nuke.root().name() else ""
    first_frame = int(nuke.root()['first_frame'].value())
    last_frame  = int(nuke.root()['last_frame'].value())

    for knob_name in FILE_KNOBS:
        knob = node.knob(knob_name)
        if not knob:
            continue
        raw_path = knob.value()
        if not raw_path or not raw_path.strip():
            continue
        if not os.path.isabs(raw_path) and script_dir:
            resolved = os.path.normpath(os.path.join(script_dir, raw_path))
        else:
            resolved = os.path.normpath(nuke.filenameFilter(raw_path))

        _, is_seq = resolve_sequence_path(resolved)
        node_first, node_last = first_frame, last_frame
        if node.knob('first') and node.knob('last'):
            try:
                node_first = int(node['first'].value())
                node_last  = int(node['last'].value())
            except Exception:
                pass
        results[knob_name] = (raw_path, resolved, is_seq, (node_first, node_last))
    return results


def collect_all_connected_nodes(seed_nodes):
    visited = set()
    queue = list(seed_nodes)
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        try:
            for dep in node.dependencies():
                if dep not in visited:
                    queue.append(dep)
        except Exception:
            pass
        try:
            for dep in node.dependent():
                if dep not in visited:
                    queue.append(dep)
        except Exception:
            pass
    return visited


def safe_copy(src, dst, overwrite=False):
    if not os.path.exists(src):
        return False, "Source not found: %s" % src
    if os.path.exists(dst) and not overwrite:
        return True, "Already exists (skipped): %s" % dst
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True, "Copied: %s" % os.path.basename(src)
    except Exception as e:
        return False, "Failed to copy %s: %s" % (src, str(e))


def safe_relpath(path, start):
    """Return relative path or basename if cross-device / UNC path."""
    try:
        rel = os.path.relpath(path, start)
        if rel.startswith("..") or os.path.isabs(rel):
            return os.path.basename(path)
        return rel
    except ValueError:
        return os.path.basename(path)


def is_footage_ext(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in ['.exr', '.dpx', '.tif', '.tiff', '.jpg', '.jpeg',
                   '.png', '.mov', '.mp4', '.avi', '.mxf', '.r3d', '.braw',
                   '.cin', '.sgi', '.tga', '.hdr', '.tx']


def categorize_root(archive_dir, path):
    ext = os.path.splitext(path)[1].lower()
    if is_footage_ext(path):
        return os.path.join(archive_dir, "footage")
    elif ext in ['.cube', '.lut', '.csp', '.3dl', '.cc', '.cdl']:
        return os.path.join(archive_dir, "luts")
    elif ext in ['.abc', '.fbx', '.obj', '.usd', '.usda', '.usdc',
                 '.geo', '.bgeo', '.vdb', '.ass']:
        return os.path.join(archive_dir, "scenes")
    else:
        return os.path.join(archive_dir, "misc")


# ---------------------------------------------
# WORKER THREAD
# ---------------------------------------------

class ArchiveWorker(QThread):
    progress = Signal(int)
    log      = Signal(str, str)
    finished = Signal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self._run_archive()
        except Exception as e:
            self.log.emit("FATAL: %s" % traceback.format_exc(), "error")
            self.finished.emit(False, str(e))

    def _run_archive(self):
        cfg            = self.config
        archive_dir    = cfg['archive_dir']
        use_selected   = cfg['use_selected']
        overwrite      = cfg['overwrite']
        save_script    = cfg['save_script']
        write_manifest = cfg['write_manifest']
        respect_range  = cfg['respect_frame_range']
        relink         = cfg['relink_paths']
        zip_archive    = cfg['zip_archive']

        self.log.emit("=" * 50, "info")
        self.log.emit("NukeArchiver v%s  --  Starting archive" % VERSION, "info")
        self.log.emit("Destination: %s" % archive_dir, "info")
        self.log.emit("=" * 50, "info")

        # -- Step 1: Collect nodes --
        self.log.emit("Collecting nodes...", "info")
        if use_selected:
            seed = nuke.selectedNodes()
            if not seed:
                self.finished.emit(False, "No nodes selected.")
                return
            cfg['_seed_nodes'] = list(seed)
            nodes = collect_all_connected_nodes(seed)
            self.log.emit("  %d selected -> %d total connected nodes" % (len(seed), len(nodes)), "info")
        else:
            nodes = set(nuke.allNodes(recurseGroups=True))
            cfg['_seed_nodes'] = list(nodes)
            self.log.emit("  All nodes: %d" % len(nodes), "info")

        self.progress.emit(5)
        if self._cancelled:
            return

        # -- Step 2: Collect file references --
        self.log.emit("Scanning file references...", "info")
        file_map = {}
        missing  = []

        for node in nodes:
            info = get_node_file_info(node)
            if info:
                file_map[node] = info

        self.log.emit("  Found %d nodes with file references" % len(file_map), "info")
        self.progress.emit(15)

        # -- Step 3: Build copy list --
        # Each Read/footage node gets its own subfolder: footage/<NodeName>/
        # Non-footage nodes (luts, scenes, misc) go into their category root.
        self.log.emit("Resolving file paths...", "info")

        # copy_tasks: (src, dst, node, knob_name, relinked_path)
        copy_tasks = []
        seen_dsts  = {}   # dst -> src (dedup)
        script_dir = os.path.dirname(nuke.root().name()) or ""

        for node, knobs in file_map.items():
            for knob_name, (raw_path, resolved, is_seq, frame_range) in knobs.items():

                if is_seq:
                    first, last = frame_range if respect_range else (None, None)
                    files = get_frame_range_files(resolved, first, last)
                    if not files:
                        missing.append((node.name(), knob_name, resolved))
                        self.log.emit(
                            "  MISSING seq: %s.%s -> %s" % (node.name(), knob_name, resolved),
                            "warn")
                        continue

                    sample = files[0]
                    cat_root = categorize_root(archive_dir, sample)

                    # Per-node subfolder for footage sequences
                    if is_footage_ext(sample):
                        node_dir = os.path.join(cat_root, node.name())
                    else:
                        node_dir = cat_root

                    for src in files:
                        fname = os.path.basename(src)
                        dst   = os.path.join(node_dir, fname)
                        if dst in seen_dsts:
                            continue
                        seen_dsts[dst] = src
                        copy_tasks.append((src, dst, node, knob_name, None))

                    # Build relinked sequence path for this node
                    first_dst  = os.path.join(node_dir, os.path.basename(files[0]))
                    relinked   = re.sub(r'\d{2,}(?=\.\w+$)', '%04d', first_dst)
                    # Update the last appended task with the relinked path
                    last = copy_tasks[-1]
                    copy_tasks[-1] = (last[0], last[1], last[2], last[3], relinked)

                else:
                    if not os.path.exists(resolved):
                        missing.append((node.name(), knob_name, resolved))
                        self.log.emit(
                            "  MISSING file: %s.%s -> %s" % (node.name(), knob_name, resolved),
                            "warn")
                        continue

                    cat_root = categorize_root(archive_dir, resolved)
                    fname    = os.path.basename(resolved)

                    # Per-node subfolder for footage files
                    if is_footage_ext(resolved):
                        node_dir = os.path.join(cat_root, node.name())
                    else:
                        node_dir = cat_root

                    dst = os.path.join(node_dir, fname)

                    if dst in seen_dsts:
                        continue
                    seen_dsts[dst] = resolved
                    copy_tasks.append((resolved, dst, node, knob_name, dst))

        self.log.emit("  %d files to copy, %d missing" % (len(copy_tasks), len(missing)), "info")
        self.progress.emit(20)

        # -- Step 4: Copy files --
        self.log.emit("Copying files...", "info")
        os.makedirs(archive_dir, exist_ok=True)

        copied   = 0
        failed   = 0
        manifest_entries = []

        for i, task in enumerate(copy_tasks):
            if self._cancelled:
                self.log.emit("Archive cancelled by user.", "warn")
                self.finished.emit(False, "Cancelled")
                return

            src, dst, node, knob_name, new_path = task
            ok, msg = safe_copy(src, dst, overwrite=overwrite)

            if ok:
                copied += 1
                self.log.emit("  [OK] %s" % os.path.basename(src), "success")
                manifest_entries.append({
                    "node": node.name(), "class": node.Class(),
                    "knob": knob_name, "source": src,
                    "destination": dst, "status": "copied"
                })
            else:
                failed += 1
                self.log.emit("  [FAIL] %s" % msg, "error")
                manifest_entries.append({
                    "node": node.name(), "class": node.Class(),
                    "knob": knob_name, "source": src,
                    "destination": dst, "status": "failed", "error": msg
                })

            progress = 20 + int((i + 1) / max(len(copy_tasks), 1) * 50)
            self.progress.emit(progress)

        # -- Step 5: Relink paths in live script (optional) --
        if relink and copy_tasks:
            self.log.emit("Relinking paths in live script...", "info")
            relink_map = {}
            for src, dst, node, knob_name, new_path in copy_tasks:
                if new_path:
                    relink_map[(node.name(), knob_name)] = new_path

            for node, knobs in file_map.items():
                for knob_name in knobs:
                    key = (node.name(), knob_name)
                    if key in relink_map:
                        try:
                            node.knob(knob_name).setValue(relink_map[key])
                            self.log.emit(
                                "  Relinked: %s.%s" % (node.name(), knob_name), "info")
                        except Exception as e:
                            self.log.emit(
                                "  Relink failed: %s.%s -- %s" % (node.name(), knob_name, e),
                                "warn")

        self.progress.emit(75)

        # -- Step 6: Save archived .nk with relinked paths --
        archive_script = None
        if save_script:
            self.log.emit("Saving archived .nk script...", "info")
            script_name = os.path.splitext(
                os.path.basename(nuke.root().name()))[0] if nuke.root().name() else "comp"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_script = os.path.join(
                archive_dir, "%s_ARCHIVE_%s.nk" % (script_name, ts))
            tmp_nk = cfg.get("_temp_nk_path")
            try:
                if tmp_nk and os.path.exists(tmp_nk):
                    shutil.move(tmp_nk, archive_script)
                else:
                    self.log.emit("  WARNING: Temp .nk not found.", "warn")
                    archive_script = None

                if archive_script and os.path.exists(archive_script):
                    # Build path relink map: original -> new archive path
                    path_relink_map = {}
                    for src, dst, node, knob_name, new_path in copy_tasks:
                        if new_path and src:
                            # Forward-slash variants (Nuke .nk format)
                            src_fwd = src.replace("\\", "/")
                            dst_fwd = new_path.replace("\\", "/")
                            path_relink_map[src_fwd] = dst_fwd
                            # Also map the sequence base pattern
                            src_pat = re.sub(r'\d{2,}(?=\.\w+$)', '%04d', src_fwd)
                            dst_pat = re.sub(r'\d{2,}(?=\.\w+$)', '%04d', dst_fwd)
                            path_relink_map[src_pat] = dst_pat

                    if path_relink_map:
                        self.log.emit("  Relinking paths in archived .nk...", "info")
                        try:
                            with open(archive_script, "r", encoding="utf-8",
                                      errors="replace") as f:
                                nk_content = f.read()

                            relinked_count = 0
                            for old_p, new_p in path_relink_map.items():
                                if old_p in nk_content:
                                    nk_content = nk_content.replace(old_p, new_p)
                                    relinked_count += 1

                            with open(archive_script, "w", encoding="utf-8") as f:
                                f.write(nk_content)

                            self.log.emit(
                                "  Relinked %d path(s) in archived script." % relinked_count,
                                "success")
                        except Exception as e:
                            self.log.emit("  Path relink failed: %s" % e, "warn")

                    node_count = cfg.get("_node_count", "?")
                    self.log.emit(
                        "  Script saved (%s nodes): %s" % (
                            node_count, os.path.basename(archive_script)),
                        "success")

            except Exception as e:
                self.log.emit("  Script save failed: %s" % e, "error")

        self.progress.emit(85)

        # -- Step 7: Write manifest --
        if write_manifest:
            self.log.emit("Writing manifest...", "info")
            manifest = {
                "archive_tool":   "NukeArchiver v%s" % VERSION,
                "timestamp":      datetime.datetime.now().isoformat(),
                "source_script":  nuke.root().name(),
                "archive_dir":    archive_dir,
                "summary": {
                    "total_files": len(copy_tasks),
                    "copied":      copied,
                    "failed":      failed,
                    "missing":     len(missing),
                },
                "missing_files": [
                    {"node": n, "knob": k, "path": p} for n, k, p in missing
                ],
                "files": manifest_entries
            }
            manifest_path = os.path.join(archive_dir, "archive_manifest.json")
            try:
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                self.log.emit("  Manifest written.", "success")
            except Exception as e:
                self.log.emit("  Manifest write failed: %s" % e, "error")

        self.progress.emit(90)

        # -- Step 8: Zip archive (optional) --
        if zip_archive:
            self.log.emit("Creating ZIP archive...", "info")
            zip_path = archive_dir.rstrip("/\\") + ".zip"
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(archive_dir):
                        for file in files:
                            abs_path = os.path.join(root, file)
                            arcname  = os.path.relpath(abs_path, os.path.dirname(archive_dir))
                            zf.write(abs_path, arcname)
                self.log.emit("  ZIP saved: %s" % os.path.basename(zip_path), "success")
            except Exception as e:
                self.log.emit("  ZIP failed: %s" % e, "error")

        self.progress.emit(100)

        summary = (
            "Archive complete.\n"
            "Files copied: %d  |  Failed: %d  |  Missing: %d\n"
            "Destination: %s" % (copied, failed, len(missing), archive_dir)
        )
        self.log.emit("", "info")
        self.log.emit("=" * 50, "info")
        self.log.emit(summary, "success")
        self.log.emit("=" * 50, "info")
        self.finished.emit(True, summary)


# ---------------------------------------------
# UI
# ---------------------------------------------

class NukeArchiverUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NukeArchiver  v%s" % VERSION)
        self.setMinimumSize(700, 740)
        self.setStyleSheet(DARK_STYLE)
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # -- Header --
        header = QtWidgets.QVBoxLayout()
        header.setSpacing(2)
        title    = QtWidgets.QLabel("NUKE ARCHIVER")
        title.setObjectName("titleLabel")
        subtitle = QtWidgets.QLabel("NODE & MATERIAL COLLECTION TOOL")
        subtitle.setObjectName("subtitleLabel")
        creator  = QtWidgets.QLabel("by  Ravihara Perera")
        creator.setObjectName("creatorLabel")
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addWidget(creator)
        main_layout.addLayout(header)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #3a3a3a;")
        main_layout.addWidget(line)

        # -- Archive Destination --
        dest_group  = QtWidgets.QGroupBox("Archive Destination")
        dest_layout = QtWidgets.QHBoxLayout(dest_group)
        self.dir_edit = QtWidgets.QLineEdit()
        self.dir_edit.setPlaceholderText("Select or type archive folder path...")
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_dir)
        dest_layout.addWidget(self.dir_edit)
        dest_layout.addWidget(browse_btn)
        main_layout.addWidget(dest_group)

        # -- Node Scope --
        scope_group  = QtWidgets.QGroupBox("Node Scope")
        scope_layout = QtWidgets.QVBoxLayout(scope_group)
        self.selected_radio = QtWidgets.QRadioButton(
            "Selected nodes + all connected upstream/downstream")
        self.all_radio = QtWidgets.QRadioButton("All nodes in script")
        self.selected_radio.setChecked(True)
        scope_layout.addWidget(self.selected_radio)
        scope_layout.addWidget(self.all_radio)
        main_layout.addWidget(scope_group)

        # -- Options --
        opts_group  = QtWidgets.QGroupBox("Options")
        opts_layout = QtWidgets.QGridLayout(opts_group)
        opts_layout.setColumnStretch(1, 1)

        self.overwrite_cb    = QtWidgets.QCheckBox("Overwrite existing files")
        self.save_script_cb  = QtWidgets.QCheckBox("Save archived .nk script copy")
        self.manifest_cb     = QtWidgets.QCheckBox("Write JSON manifest log")
        self.relink_cb       = QtWidgets.QCheckBox("Relink paths in current (live) script")
        self.frame_range_cb  = QtWidgets.QCheckBox("Respect node frame ranges")
        self.zip_cb          = QtWidgets.QCheckBox("Zip entire archive after completion")

        self.save_script_cb.setChecked(True)
        self.manifest_cb.setChecked(True)
        self.frame_range_cb.setChecked(True)

        opts_layout.addWidget(self.overwrite_cb,   0, 0)
        opts_layout.addWidget(self.save_script_cb, 0, 1)
        opts_layout.addWidget(self.manifest_cb,    1, 0)
        opts_layout.addWidget(self.relink_cb,      1, 1)
        opts_layout.addWidget(self.frame_range_cb, 2, 0)
        opts_layout.addWidget(self.zip_cb,         2, 1)
        main_layout.addWidget(opts_group)

        # -- Folder Structure Preview --
        struct_group  = QtWidgets.QGroupBox("Archive Folder Structure")
        struct_layout = QtWidgets.QVBoxLayout(struct_group)
        struct_text   = QtWidgets.QLabel(
            "  archive_root/\n"
            "  +-- footage/\n"
            "  |   +-- ReadNode1/    (files for Read node 1)\n"
            "  |   +-- ReadNode2/    (files for Read node 2)\n"
            "  +-- luts/\n"
            "  +-- scenes/\n"
            "  +-- misc/\n"
            "  +-- comp_ARCHIVE_YYYYMMDD_HHMMSS.nk   (relinked)\n"
            "  +-- archive_manifest.json\n"
            "  [archive_root.zip]    (if Zip option enabled)"
        )
        struct_text.setStyleSheet("color: #888; font-size: 11px;")
        struct_layout.addWidget(struct_text)
        main_layout.addWidget(struct_group)

        # -- Progress --
        progress_group  = QtWidgets.QGroupBox("Progress")
        progress_layout = QtWidgets.QVBoxLayout(progress_group)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.status_label = QtWidgets.QLabel("Ready.")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        main_layout.addWidget(progress_group)

        # -- Log --
        log_group  = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        self.log_edit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(140)
        log_layout.addWidget(self.log_edit)
        main_layout.addWidget(log_group)

        # -- Buttons --
        btn_layout = QtWidgets.QHBoxLayout()
        self.scan_btn    = QtWidgets.QPushButton("Scan Nodes")
        self.scan_btn.clicked.connect(self._scan_nodes)
        self.cancel_btn  = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        self.archive_btn = QtWidgets.QPushButton("Archive")
        self.archive_btn.setObjectName("archiveBtn")
        self.archive_btn.clicked.connect(self._start_archive)
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(self.archive_btn)
        main_layout.addLayout(btn_layout)

        # -- Footer --
        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)

        copyright_label = QtWidgets.QLabel(
            "(c) 2026 Ravihara Perera. All Rights Reserved.")
        copyright_label.setObjectName("copyrightLabel")

        update_btn = QtWidgets.QPushButton("Check for Updates")
        update_btn.setObjectName("updateBtn")
        update_btn.setFixedWidth(130)
        update_btn.clicked.connect(self._check_for_updates)

        footer_layout.addWidget(copyright_label)
        footer_layout.addStretch()
        footer_layout.addWidget(update_btn)
        main_layout.addLayout(footer_layout)

    def _check_for_updates(self):
        try:
            req = urllib.request.Request(
                UPDATE_URL,
                headers={"User-Agent": "NukeArchiver/%s" % VERSION}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                latest = resp.read().decode("utf-8").strip()

            def _ver_tuple(v):
                try:
                    return tuple(int(x) for x in v.split("."))
                except Exception:
                    return (0,)

            if _ver_tuple(latest) > _ver_tuple(VERSION):
                QtWidgets.QMessageBox.information(
                    self,
                    "Update Available",
                    "A new version of NukeArchiver is available!\n\n"
                    "  Installed : v%s\n"
                    "  Latest    : v%s\n\n"
                    "Download the latest version from your Gumroad library." % (
                        VERSION, latest)
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Up to Date",
                    "You are running the latest version of NukeArchiver (v%s)." % VERSION
                )
        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            QtWidgets.QMessageBox.warning(
                self,
                "Update Check Failed",
                "Could not reach the update server.\n\n"
                "Reason: %s\n\n"
                "Possible causes:\n"
                "  - No internet connection\n"
                "  - version.txt not yet created on GitHub\n"
                "  - Firewall blocking Nuke's network access\n\n"
                "URL checked:\n%s" % (reason, UPDATE_URL)
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Update Check Failed",
                "Update check encountered an error:\n\n%s\n\nURL: %s" % (
                    traceback.format_exc(), UPDATE_URL)
            )

    def _browse_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Archive Directory",
            self.dir_edit.text() or os.path.expanduser("~"))
        if path:
            self.dir_edit.setText(path)

    def _log(self, message, level="info"):
        colors = {
            "info":    "#a0a0a0",
            "warn":    "#e0c040",
            "error":   "#e05050",
            "success": "#60c060",
        }
        color = colors.get(level, "#a0a0a0")
        self.log_edit.append('<span style="color:%s;">%s</span>' % (color, message))
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum())

    def _scan_nodes(self):
        self.log_edit.clear()
        use_selected = self.selected_radio.isChecked()

        if use_selected:
            seed = nuke.selectedNodes()
            if not seed:
                self._log("No nodes selected. Select nodes in Nuke first.", "warn")
                return
            nodes = collect_all_connected_nodes(seed)
        else:
            nodes = set(nuke.allNodes(recurseGroups=True))

        self._log("Nodes in scope: %d" % len(nodes), "info")
        file_count    = 0
        missing_count = 0
        seq_count     = 0

        for node in nodes:
            info = get_node_file_info(node)
            for knob_name, (raw, resolved, is_seq, frame_range) in info.items():
                if is_seq:
                    files = get_frame_range_files(resolved)
                    seq_count += 1
                    if files:
                        file_count += len(files)
                        self._log(
                            "  SEQ  %s.%s  [%d frames]  -> footage/%s/" % (
                                node.name(), knob_name, len(files), node.name()), "info")
                    else:
                        missing_count += 1
                        self._log(
                            "  MISS %s.%s  %s" % (node.name(), knob_name, resolved), "warn")
                else:
                    exists = os.path.exists(resolved)
                    file_count    += 1 if exists else 0
                    missing_count += 0 if exists else 1
                    status = "FILE" if exists else "MISS"
                    level  = "info" if exists else "warn"
                    dest   = ("footage/%s/" % node.name()) if is_footage_ext(resolved) else "category/"
                    self._log(
                        "  %s %s.%s  -> %s" % (status, node.name(), knob_name, dest), level)

        self._log("", "info")
        self._log(
            "Scan complete: %d files | %d sequences | %d missing" % (
                file_count, seq_count, missing_count), "success")
        self.status_label.setText(
            "Scan: %d files | %d sequences | %d missing" % (
                file_count, seq_count, missing_count))

    def _get_config(self):
        return {
            "archive_dir":        self.dir_edit.text().strip(),
            "use_selected":       self.selected_radio.isChecked(),
            "overwrite":          self.overwrite_cb.isChecked(),
            "save_script":        self.save_script_cb.isChecked(),
            "write_manifest":     self.manifest_cb.isChecked(),
            "relink_paths":       self.relink_cb.isChecked(),
            "respect_frame_range": self.frame_range_cb.isChecked(),
            "zip_archive":        self.zip_cb.isChecked(),
        }

    def _start_archive(self):
        cfg = self._get_config()

        if not cfg["archive_dir"]:
            QtWidgets.QMessageBox.warning(
                self, "No Destination", "Please select an archive destination folder.")
            return

        if not os.path.exists(cfg["archive_dir"]):
            reply = QtWidgets.QMessageBox.question(
                self, "Create Directory",
                "Directory does not exist:\n%s\n\nCreate it?" % cfg["archive_dir"],
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return
            os.makedirs(cfg["archive_dir"], exist_ok=True)

        if cfg["relink_paths"]:
            reply = QtWidgets.QMessageBox.warning(
                self, "Relink Warning",
                "Relinking will modify file paths in your CURRENT live script.\n"
                "Make sure you have saved your script first.\n\nContinue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return

        # -- nodeCopy MUST run on the main thread --
        cfg["_temp_nk_path"] = None
        cfg["_node_count"]   = 0

        if cfg["save_script"]:
            use_selected = cfg["use_selected"]
            try:
                if use_selected:
                    seed = nuke.selectedNodes()
                    if not seed:
                        QtWidgets.QMessageBox.warning(
                            self, "No Selection", "No nodes selected.")
                        return
                    nodes_to_save = collect_all_connected_nodes(seed)
                else:
                    nodes_to_save = set(nuke.allNodes(recurseGroups=True))

                cfg["_node_count"] = len(nodes_to_save)

                # Save and restore selection
                orig_selected = [n for n in nuke.allNodes() if n.isSelected()]
                for n in nuke.allNodes():
                    n.setSelected(False)
                for n in nodes_to_save:
                    n.setSelected(True)

                tmp = tempfile.NamedTemporaryFile(
                    suffix=".nk", delete=False, dir=cfg["archive_dir"])
                tmp_path = tmp.name
                tmp.close()
                nuke.nodeCopy(tmp_path)
                cfg["_temp_nk_path"] = tmp_path

                for n in nuke.allNodes():
                    n.setSelected(False)
                for n in orig_selected:
                    try:
                        n.setSelected(True)
                    except Exception:
                        pass

            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Node Export Failed",
                    "Could not export nodes:\n%s" % e)
                return

        self.log_edit.clear()
        self.progress_bar.setValue(0)
        self.archive_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.scan_btn.setEnabled(False)
        self.status_label.setText("Archiving...")

        self.worker = ArchiveWorker(cfg)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelling...")

    def _on_finished(self, success, summary):
        self.archive_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.scan_btn.setEnabled(True)
        if success:
            self.status_label.setText("Archive complete.")
            QtWidgets.QMessageBox.information(self, "Archive Complete", summary)
        else:
            self.status_label.setText("Archive failed: %s" % summary)
            if summary != "Cancelled":
                QtWidgets.QMessageBox.critical(self, "Archive Failed", summary)


# ---------------------------------------------
# ENTRY POINT
# ---------------------------------------------

_archiver_instance = None

def show():
    global _archiver_instance
    try:
        main_window = QtWidgets.QApplication.activeWindow()
    except Exception:
        main_window = None
    _archiver_instance = NukeArchiverUI(parent=main_window)
    _archiver_instance.show()
    _archiver_instance.raise_()
    _archiver_instance.activateWindow()
    return _archiver_instance


def add_to_menu():
    menubar = nuke.menu("Nuke")
    pipeline_menu = menubar.addMenu("Pipeline")
    pipeline_menu.addCommand("NukeArchiver", show, "")


if __name__ == "__main__":
    show()
