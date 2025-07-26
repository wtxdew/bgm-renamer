#!/usr/bin/env python3
import os
import re
import json
import argparse
import shutil
import colorlog
from pathlib import Path  # make sure this is imported
from typing import Dict, Optional

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }))

logger = colorlog.getLogger('myapp')
logger.addHandler(handler)
logger.setLevel('DEBUG')


def parse_file_name(path_name: str) -> Dict:
    original = path_name
    subtitle_groups = []
    video_format_parts = []
    episode_range = None

    name = Path(original).name  # Extracts the last part of the path
    dir = name
    root = str(Path(original).parent)

    # Step 1: Extract all bracketed sections
    bracket_sections = re.findall(r'\[(.*?)\]', name)

    # Step 2: First bracket is usually group
    if bracket_sections:
        first = bracket_sections[0]
        # support &-joined groups
        subtitle_groups = [g.strip() for g in first.split("&")]
        name = name.replace(f"[{first}]", "").strip()

    # Step 3: Remaining brackets are format/episode info
    for b in bracket_sections[1:]:
        if re.search(r'\d{1,2}\s*-\s*\d{1,3}', b):  # like 01-12
            episode_range = b.strip()
        else:
            video_format_parts.append(b.strip())

        name = name.replace(f"[{b}]", "").strip()

    # Step 4: Clean leading dash / extra characters
    name = re.sub(r'^[-\s]+', '', name)
    series_name = name.strip()

    return {
        "series_name": series_name,
        "subtitle_groups": subtitle_groups,
        "video_format": video_format_parts,
        "episode_range": episode_range,
        "raw": original,
        "root": root,
        "dir": dir
    }


def parse_episode_number(filename: str) -> Optional[int]:
    match = re.search(r'[\s\-\[](\d{2,3})(?=[\]\s\.])', filename)
    return int(match.group(1)) if match else None


def link_file_loop(src_dir, dst_dir, series_name="", dry_run=False):
    ignore_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.xz', '.png']
    ignore_file = ['.DS_Store']
    logger.info(f"Source directory: {src_dir}")
    logger.info(f"Target directory: {dst_dir}")
    for file in src_dir.iterdir():
        if file.is_file() and file.suffix not in ignore_exts:
            if file.name in ignore_file:
                logger.debug(f"SKIP file: {file.name}")
                continue
            ep_num = parse_episode_number(file.name)
            if ep_num is not None:
                new_filename = f"{series_name} S01E{ep_num:02d}{file.suffix}"
            else:
                sp_name = parse_file_name(file)['video_format'][0]
                new_filename = f"{sp_name}{file.suffix}"
            dst_file = dst_dir / new_filename
            logger.info(f"{new_filename} <- {file.name}")
            logger.debug(f"<< SRC File: {file}")
            logger.debug(f">> DST File: {dst_file}")
            if dry_run:
                logger.debug("[DRY RUN] Would link: SRC -> DST")
            else:
                logger.error("RUN")
                # os.link(file, dst_file)


def rearrange_directory(meta: dict, dry_run=False):
    series_name = meta['series_name']
    src_root = Path(meta['root'])
    src_dir = Path(meta['raw'])
    dst_root = Path("/Volumes/NAS_SSD/Media/Anime")
    dst_dir = dst_root / series_name
    if dry_run:
        logger.debug(f"[DRY RUN] Would create DST directory: {dst_dir}")
    else:
        dst_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"name: {series_name}")
    logger.debug(f"root: {src_root}")
    logger.debug(f"src dir: {src_dir}")
    logger.debug(f"dst dir: {dst_dir}")

    dst_season = dst_dir / "Season 01"
    dst_extras = dst_dir / "extras"
    if dry_run:
        logger.debug(f"[DRY RUN] Would create directory: {dst_season}")
        logger.debug(f"[DRY RUN] Would create directory: {dst_extras}")
    else:
        dst_season.mkdir(parents=True, exist_ok=True)
        dst_extras.mkdir(parents=True, exist_ok=True)

    # Season Episode
    logger.info("Start Season Episode")
    # for file in src_dir.iterdir():
    #     if file.is_file() and file.suffix not in ignore_exts:
    #         if file.name in ignore_file:
    #             print(f"[SKIP] file ignored: {file.name}")
    #             continue
    #         ep_num = parse_episode_number(file.name)
    #         if ep_num is not None:
    #             new_filename = f"{series_name} S01E{ep_num:02d}{file.suffix}"
    #             dst_file = dst_season / new_filename
    #             logger.info(f"{file.name} -> {new_filename}")
    #             logger.info(f"<< SRC File: {file}")
    #             logger.info(f">> DST File: {dst_file}")
    #             if dry_run:
    #                 logger.debug("[DRY RUN] Would link: SRC -> DST")
    #             else:
    #                 os.link(file, dst_file)

    link_file_loop(src_dir, dst_season, series_name, dry_run)

    # SPs Video
    logger.info("## START SPs VIDEO")
    special_dir = src_dir / "SPs"
    if special_dir.exists() and special_dir.is_dir():
        link_file_loop(special_dir, dst_extras, series_name, dry_run)
        # for file in special_dir.iterdir():
        #     if not file.is_file() or file.suffix in ignore_exts:
        #         logger.debug(f"Skip {file.name}")
        #         continue
        #     sp_name = parse_file_name(file)['video_format'][0]
        #     dst_file_name = f"{sp_name}{file.suffix}"
        #     dst_file = dst_extras / dst_file_name
        #     logger.info(f"{file.name} -> {dst_file_name}")
        #     logger.info(f"SRC File: {file}")
        #     logger.info(f"DST File: {dst_file}")
        #     if dry_run:
        #         logger.debug("[DRY RUN] Would link: SRC -> DST")
        #     else:
        #         os.link(file, dst_file)

    orig_path = "/Volumes/NAS_SSD/Media/orig/"
    orig_dir = Path(orig_path) / meta['dir']

    logger.info(f"Moving SRC to : {orig_dir}")
    if dry_run:
        logger.debug(f"[DRY RUN] SRC Would Move: {orig_dir}")
    elif not orig_dir.noexists():
        shutil.move(src_dir, orig_dir)
    else:
        logger.warn(f"[WARNING] Directory exists: {orig_dir}")


def main():
    # logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description="Parse anime folder names.")
    parser.add_argument('names', nargs='+', help='Folder name(s) to parse')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying anything.')
    args = parser.parse_args()
    dry_run = args.dry_run

    for path_str in args.names:
        meta_dir = parse_file_name(path_str)
        print(json.dumps(meta_dir, indent=2, ensure_ascii=False))
        rearrange_directory(meta_dir, dry_run)


if __name__ == '__main__':
    main()
