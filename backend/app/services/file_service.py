import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import DATA_DIR


class FileNotFoundError(Exception):
    pass


class RowNotFoundError(Exception):
    pass


def parse_text_to_conversations(text: str) -> Dict[str, Any]:
    conversations = []
    pattern = r'(User|Assistant):\s*([\s\S]*?)(?=(?:User|Assistant):|$)'
    import re
    for match in re.finditer(pattern, text):
        role = match.group(1).lower()
        content = match.group(2).strip()
        if content.endswith('\n'):
            content = content[:-1]
        conversations.append({'role': role, 'content': content})
    rounds = (len(conversations) + 1) // 2
    return {'conversations': conversations, 'rounds': rounds}


def get_folder_list() -> List[str]:
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    folders = ['./']
    folders += [f'./{f.name}' for f in DATA_DIR.iterdir() if f.is_dir() and not f.name.startswith('.')]
    return sorted(folders)


def get_file_list(folder: str = None) -> List[str]:
    if not folder:
        folder = ''
    target_dir = DATA_DIR / folder if folder else DATA_DIR
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
    files = [f.name for f in target_dir.iterdir() if f.suffix == '.jsonl']
    return sorted(files)


def get_file_path(filename: str, folder: str = None) -> Path:
    if not folder:
        folder = ''
    folder_path = DATA_DIR / folder if folder else DATA_DIR
    filepath = folder_path / filename
    if not filepath.exists():
        raise FileNotFoundError(f"文件 {filename} 不存在")
    return filepath


def read_jsonl(filename: str, folder: str = None, page: int = 1, size: int = 10, rounds_filter: str = "all") -> Dict[str, Any]:
    filepath = get_file_path(filename, folder)
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                text = data.get('text', '')
                parsed = parse_text_to_conversations(text)
                rows.append({
                    'id': line_num,
                    'text': text,
                    **parsed
                })
            except json.JSONDecodeError:
                rows.append({
                    'id': line_num,
                    'text': line,
                    'conversations': [],
                    'rounds': 0
                })
    
    if rounds_filter == "single":
        rows = [r for r in rows if r.get('rounds', 0) == 1]
    elif rounds_filter == "multi":
        rows = [r for r in rows if r.get('rounds', 0) > 1]
    
    total = len(rows)
    start = (page - 1) * size
    end = start + size
    page_data = rows[start:end]
    return {'total': total, 'data': page_data}


def update_row(filename: str, folder: str, row_id: int, new_text: str) -> bool:
    filepath = get_file_path(filename, folder)
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            rows.append(line)
    if row_id < 1 or row_id > len(rows):
        raise RowNotFoundError(f"行号 {row_id} 不存在")
    new_data = {'text': new_text}
    rows[row_id - 1] = json.dumps(new_data, ensure_ascii=False) + '\n'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(rows)
    return True


def delete_row(filename: str, folder: str, row_id: int) -> bool:
    filepath = get_file_path(filename, folder)
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            rows.append(line)
    if row_id < 1 or row_id > len(rows):
        raise RowNotFoundError(f"行号 {row_id} 不存在")
    rows.pop(row_id - 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(rows)
    return True


def delete_file(filename: str, folder: str = None) -> bool:
    filepath = get_file_path(filename, folder)
    if filepath.exists():
        filepath.unlink()
        return True
    raise FileNotFoundError(f"文件 {filename} 不存在")


def merge_files(source_files: List[Dict[str, str]], shuffle: bool, new_name: str, folder: str = None) -> str:
    all_rows = []
    for item in source_files:
        filepath = get_file_path(item['filename'], item.get('folder'))
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    all_rows.append(line)
    if shuffle:
        random.shuffle(all_rows)
    if not new_name.endswith('.jsonl'):
        new_name += '.jsonl'
    
    if folder:
        output_dir = DATA_DIR / folder
    else:
        output_dir = DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / new_name
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in all_rows:
            f.write(row + '\n')
    return new_name


def count_file_lines(filename: str, folder: str = None) -> int:
    filepath = get_file_path(filename, folder)
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def get_file_stats(filename: str, folder: str = None) -> Dict[str, Any]:
    filepath = get_file_path(filename, folder)
    line_count = count_file_lines(filename, folder)
    return {
        'filename': filename,
        'folder': folder or '',
        'line_count': line_count
    }


def get_files_stats(filenames: List[str], folders: List[str] = None) -> List[Dict[str, Any]]:
    if folders is None:
        folders = [''] * len(filenames)
    stats = []
    for filename, folder in zip(filenames, folders):
        try:
            stats.append(get_file_stats(filename, folder))
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {folder}/{filename} 不存在")
    return stats


def merge_files_with_ratio(
    source_files: List[Dict[str, str]],
    shuffle: bool,
    new_name: str,
    counts: Dict[str, int],
    folder: str = None
) -> Dict[str, Any]:
    if not source_files:
        raise ValueError("请至少选择一个源文件")

    total_original_lines = 0
    merged_rows = []
    
    for item in source_files:
        filename = item['filename']
        flder = item.get('folder', '')
        
        filepath = get_file_path(filename, flder)
        
        file_rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    file_rows.append(line)
        
        line_count = len(file_rows)
        total_original_lines += line_count
        
        key = f"{flder}/{filename}" if flder else filename
        count = counts.get(key, 0)
        
        actual_count = min(count, line_count)
        if actual_count > 0:
            sampled = random.sample(file_rows, actual_count)
            merged_rows.extend(sampled)
    
    if shuffle:
        random.shuffle(merged_rows)

    if not new_name.endswith('.jsonl'):
        new_name += '.jsonl'
    
    if folder:
        output_dir = DATA_DIR / folder
    else:
        output_dir = DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / new_name
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in merged_rows:
            f.write(row + '\n')
    
    return {
        'filename': new_name,
        'folder': folder or '',
        'total_lines': len(merged_rows),
        'original_lines': total_original_lines
    }
