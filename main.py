#!/usr/bin/env python3
import os
import re
import json
import argparse
import shutil
import logging
import colorlog
from pathlib import Path  # make sure this is imported
from typing import Dict, Optional


class DryRunFilter(logging.Filter):
    def __init__(self, name="", is_dry_run=False):
        super().__init__(name)
        self.is_dry_run = is_dry_run

    def filter(self, record):
        if self.is_dry_run and record.levelname == "INFO":
            record.levelname = "DRYRUN"
            record.levelno = logging.INFO
        return True


handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "DRYRUN": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)

logger = colorlog.getLogger("myapp")
dry_run_filter = DryRunFilter(is_dry_run=False)
logger.addFilter(dry_run_filter)
logger.addHandler(handler)
# Default level will be set by configure_logging function


def configure_logging(level_name: str) -> None:
    """Configure the logging level for the application.

    Args:
        level_name: The logging level name (case-insensitive)

    Raises:
        ValueError: If the level name is not a valid logging level
    """
    # Convert to uppercase for consistency
    level_name = level_name.upper()

    # Validate the logging level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level_name not in valid_levels:
        raise ValueError(
            f"Invalid log level '{level_name}'. Valid levels are: {', '.join(valid_levels)}"
        )

    # Get the numeric level and set it
    numeric_level = getattr(logging, level_name)
    logger.setLevel(numeric_level)


def parse_file_name(path: Path) -> Dict:
    original = path
    subtitle_groups = []
    video_format_parts = []
    episode_range = None

    name = original.name
    dir = name
    root = str(original.parent)

    # Step 1: Extract all bracketed sections
    bracket_sections = re.findall(r"\[(.*?)\]", name)

    # Step 2: First bracket is usually group
    if bracket_sections:
        first = bracket_sections[0]
        # support &-joined groups
        subtitle_groups = [g.strip() for g in first.split("&")]
        name = name.replace(f"[{first}]", "").strip()

    # Step 3: Remaining brackets are format/episode info
    for b in bracket_sections[1:]:
        if re.search(EPISODE_RANGE_PATTERN, b):  # like 01-12
            episode_range = b.strip()
        else:
            video_format_parts.append(b.strip())

        name = name.replace(f"[{b}]", "").strip()

    # Step 4: Clean leading dash / extra characters
    name = re.sub(r"^[-\s]+", "", name)
    series_name = name.strip()

    return {
        "series_name": series_name,
        "subtitle_groups": subtitle_groups,
        "video_format": video_format_parts,
        "episode_range": episode_range,
        "raw": str(original),
        "root": root,
        "dir": dir,
    }


# Episode number patterns: support multiple formats
EPISODE_PATTERN_BRACKET = r"[\s\-\[](\d{2,3})(?=[\]\s\.])"  # Original [01] format
EPISODE_PATTERN_SXX_EXX = r"S\d{1,2}E(\d{1,3})"  # S01E01, S1E1 format
EPISODE_PATTERN_JAPANESE = r"第(\d{1,3})話"  # Japanese 第08話 format
# Episode range pattern: like "01-12"
EPISODE_RANGE_PATTERN = r"\d{1,2}\s*-\s*\d{1,3}"
# Season number patterns: support multiple formats
SEASON_PATTERN_SEASON = r"Season\s+(\d{1,2})"  # "Season 2"
SEASON_PATTERN_SXX = r"S(\d{1,2})(?:E\d+)?"  # "S02" or "S02E01"
SEASON_PATTERN_JAPANESE = r"第(\d{1,2})期"  # Japanese "第2期"
# Language code pattern: matches language codes before subtitle file extensions
LANGUAGE_CODE_PATTERN = (
    r"\.([A-Za-z]{2,4}(?:-[A-Za-z]{2,4})?(?:-[A-Za-z]{4})?)(?=\.(ass|srt|vtt|sub|ssa)$)"
)
# Special content patterns: recognize various special content indicators
SPECIAL_CONTENT_PATTERN = r"(SPs?|OVA|OAD|映像特典|特典|Specials?|Extras?|Bonus)"


def parse_episode_number(filename: str) -> Optional[int]:
    """Parse episode number from filename using multiple patterns.

    Args:
        filename: The filename to parse

    Returns:
        The episode number if found, None otherwise

    Examples:
        '[Group] Series [01].mkv' -> 1
        'Tower.of.God.S02E23.mkv' -> 23
        '[Snow-Raws] ばらかもん 第08話.mkv' -> 8
    """
    # Try bracket format first (original pattern)
    match = re.search(EPISODE_PATTERN_BRACKET, filename)
    if match:
        return int(match.group(1))

    # Try SxxExx format
    match = re.search(EPISODE_PATTERN_SXX_EXX, filename)
    if match:
        return int(match.group(1))

    # Try Japanese format
    match = re.search(EPISODE_PATTERN_JAPANESE, filename)
    if match:
        return int(match.group(1))

    return None


def parse_season_number(path_or_filename: str) -> int:
    """Parse season number from folder name or filename.

    Args:
        path_or_filename: The path or filename to parse

    Returns:
        The season number if found, defaults to 1

    Examples:
        'Series Name Season 2' -> 2
        'Tower.of.God.S02E23.mkv' -> 2
        'Series 第2期' -> 2
        'Regular Series' -> 1 (default)
    """
    # Try "Season X" format
    match = re.search(SEASON_PATTERN_SEASON, path_or_filename, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Try "SXX" format
    match = re.search(SEASON_PATTERN_SXX, path_or_filename)
    if match:
        return int(match.group(1))

    # Try Japanese format
    match = re.search(SEASON_PATTERN_JAPANESE, path_or_filename)
    if match:
        return int(match.group(1))

    return 1  # Default to season 1


def is_special_content(path_or_filename: str) -> bool:
    """Check if the path or filename indicates special content.

    Args:
        path_or_filename: The path or filename to check

    Returns:
        True if it's special content, False otherwise

    Examples:
        'SPs' -> True
        '映像特典' -> True
        'OVA' -> True
        'regular_episode.mkv' -> False
    """
    return bool(re.search(SPECIAL_CONTENT_PATTERN, path_or_filename, re.IGNORECASE))


def extract_language_code(filename: str) -> Optional[str]:
    """Extract language code from subtitle files.

    Args:
        filename: The filename to parse

    Returns:
        The language code if found, None otherwise

    Examples:
        'file.JPTC.ass' -> 'JPTC'
        'file.zh-TW.srt' -> 'zh-TW'
        'file.zh-Hans.vtt' -> 'zh-Hans'
        'file.mp4' -> None
    """
    match = re.search(LANGUAGE_CODE_PATTERN, filename)
    return match.group(1) if match else None


def link_file_loop(
    src_dir: Path,
    dst_dir: Path,
    series_name: str = "",
    season_num: int = 1,
    dry_run: bool = False,
) -> None:
    file_path_list = []
    ignore_exts = [".zip", ".rar", ".7z", ".tar", ".gz", ".xz", ".png", ".txt"]
    ignore_file = [".DS_Store"]
    logger.info(f"Source directory: {src_dir}")
    logger.info(f"Target directory: {dst_dir}")
    logger.info("Would link: Source -> Target")
    for file in src_dir.iterdir():
        if file.is_file() and file.suffix not in ignore_exts:
            if file.name in ignore_file:
                logger.debug(f"SKIP file: {file.name}")
                continue
            # Extract language code for subtitle files
            language_code = extract_language_code(file.name)
            logger.debug(f"language_code: {language_code}")

            ep_num = parse_episode_number(file.name)
            logger.debug(f"ep_num: {ep_num}")
            if src_dir.name == series_name:
                is_episode = True
            else:
                is_episode = False

            if ep_num is not None and is_episode:
                # Regular episode file
                if language_code:
                    new_filename = f"{series_name} S{season_num:02d}E{ep_num:02d}.{language_code}{file.suffix}"
                else:
                    new_filename = (
                        f"{series_name} S{season_num:02d}E{ep_num:02d}{file.suffix}"
                    )
            else:
                # Special file
                video_formats = parse_file_name(file)["video_format"]
                sp_name = video_formats[0] if video_formats else "NO_NAME"
                if language_code:
                    new_filename = f"{sp_name}.{language_code}{file.suffix}"
                else:
                    new_filename = f"{sp_name}{file.suffix}"

            dst_file = dst_dir / new_filename
            num_this = len(file_path_list) + 1
            if dst_file in file_path_list:
                number = file_path_list.index(dst_file) + 1
                logger.warning(
                    f"{num_this:02d}. duplicate with {number:02d}. :{new_filename} <- {file.name}"
                )
            else:
                logger.info(f"{num_this:02d}. {new_filename} <- {file.name}")
            file_path_list.append(dst_file)
            logger.debug(f"<< SRC File: {file}")
            logger.debug(f">> DST File: {dst_file}")
            if not dry_run:
                try:
                    os.link(file, dst_file)
                except OSError as e:
                    logger.error(f"Failed to link {file} -> {dst_file}: {e}")
                    exit(255)


def rearrange_directory(
    meta: Dict[str, str],
    dry_run: bool = False,
) -> None:
    dst_root = Path("/Volumes/NAS_SSD/Media/Anime")
    orig_root = Path("/Volumes/NAS_SSD/Media/orig")
    series_name = meta["series_name"]
    src_root = Path(meta["root"])
    src_dir = Path(meta["raw"])
    dst_dir = dst_root / series_name

    # Detect season number from folder name or directory structure
    season_num = parse_season_number(str(src_dir))
    logger.debug(f"detected season: {season_num}")

    if dry_run:
        logger.info(f"[DRY RUN] Would create DST directory: {dst_dir}")
    else:
        dst_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"name: {series_name}")
    logger.debug(f"root: {src_root}")
    logger.debug(f"src dir: {src_dir}")
    logger.debug(f"dst dir: {dst_dir}")

    dst_season = dst_dir / f"Season {season_num:02d}"
    dst_extras = dst_dir / "extras"
    if dry_run:
        logger.info(f"[DRY RUN] Would create directory: {dst_season}")
        logger.info(f"[DRY RUN] Would create directory: {dst_extras}")
    else:
        dst_season.mkdir(parents=True, exist_ok=True)
        dst_extras.mkdir(parents=True, exist_ok=True)

    # Season Episode
    logger.info("Start Season Episode")
    link_file_loop(src_dir, dst_season, series_name, season_num, dry_run)

    # Enhanced Special Content Detection
    logger.info("## START SPECIAL CONTENT")

    # Check for traditional "SPs" folder
    special_dir = src_dir / "SPs"
    if special_dir.exists() and special_dir.is_dir():
        link_file_loop(special_dir, dst_extras, series_name, season_num, dry_run)

    # Check for other special content folders
    special_folders = ["映像特典", "特典", "OVA", "OAD", "Specials", "Extras", "Bonus"]
    for folder_name in special_folders:
        special_path = src_dir / folder_name
        if special_path.exists() and special_path.is_dir():
            logger.info(f"Found special content folder: {folder_name}")
            link_file_loop(special_path, dst_extras, series_name, season_num, dry_run)

    orig_dir = orig_root / meta["dir"]

    logger.info(f"Moving SRC to : {orig_dir}")
    if dry_run:
        logger.info(f"[DRY RUN] SRC Would Move: {orig_dir}")
    elif not orig_dir.exists():
        shutil.move(src_dir, orig_dir)
    else:
        logger.warning(f"[WARNING] Directory exists: {orig_dir}")


def main():
    parser = argparse.ArgumentParser(description="Parse anime folder names.")
    parser.add_argument("names", nargs="+", help="Folder name(s) to parse")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying anything.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO",
    )
    args = parser.parse_args()

    # Configure logging level
    try:
        configure_logging(args.log_level)
    except ValueError as e:
        parser.error(str(e))
        exit(1)

    dry_run = args.dry_run
    dry_run_filter.is_dry_run = dry_run

    for path_str in args.names:
        path = Path(path_str)
        if not path.exists():
            logger.error(f"Path does not exist: {path_str}")
            continue
        if not path.is_dir():
            logger.error(f"Path is not a directory: {path_str}")
            continue
        meta_dir = parse_file_name(path)
        print(json.dumps(meta_dir, indent=2, ensure_ascii=False))
        rearrange_directory(meta_dir, dry_run)


if __name__ == "__main__":
    main()
