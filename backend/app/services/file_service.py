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


def get_file_list() -> List[str]:
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = [f.name for f in DATA_DIR.iterdir() if f.suffix == '.jsonl']
    return sorted(files)


def get_file_path(filename: str) -> Path:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"文件 {filename} 不存在")
    return filepath


def read_jsonl(filename: str, page: int = 1, size: int = 10) -> Dict[str, Any]:
    filepath = get_file_path(filename)
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
    total = len(rows)
    start = (page - 1) * size
    end = start + size
    page_data = rows[start:end]
    return {'total': total, 'data': page_data}


def update_row(filename: str, row_id: int, new_text: str) -> bool:
    filepath = get_file_path(filename)
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


def delete_row(filename: str, row_id: int) -> bool:
    filepath = get_file_path(filename)
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


def merge_files(source_files: List[str], shuffle: bool, new_name: str) -> str:
    all_rows = []
    for filename in source_files:
        filepath = get_file_path(filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    all_rows.append(line)
    if shuffle:
        random.shuffle(all_rows)
    if not new_name.endswith('.jsonl'):
        new_name += '.jsonl'
    output_path = DATA_DIR / new_name
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in all_rows:
            f.write(row + '\n')
    return new_name


def count_file_lines(filename: str) -> int:
    filepath = get_file_path(filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def get_file_stats(filename: str) -> Dict[str, Any]:
    filepath = get_file_path(filename)
    line_count = count_file_lines(filename)
    return {
        'filename': filename,
        'line_count': line_count
    }


def get_files_stats(filenames: List[str]) -> List[Dict[str, Any]]:
    stats = []
    for filename in filenames:
        try:
            stats.append(get_file_stats(filename))
        except FileNotFoundError:
            raise FileNotFoundError(f"文件 {filename} 不存在")
    return stats


def merge_files_with_ratio(
    source_files: List[str],
    shuffle: bool,
    new_name: str,
    counts: Dict[str, int]
) -> Dict[str, Any]:
    if not source_files:
        raise ValueError("请至少选择一个源文件")

    file_stats = get_files_stats(source_files)
    total_original_lines = sum(f['line_count'] for f in file_stats)
    
    merged_rows = []
    
    for stat in file_stats:
        filename = stat['filename']
        filepath = get_file_path(filename)
        count = counts.get(filename, 0)
        
        file_rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    file_rows.append(line)
        
        actual_count = min(count, len(file_rows))
        sampled = random.sample(file_rows, actual_count)
        merged_rows.extend(sampled)
    
    if shuffle:
        random.shuffle(merged_rows)

    if not new_name.endswith('.jsonl'):
        new_name += '.jsonl'
    output_path = DATA_DIR / new_name
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in merged_rows:
            f.write(row + '\n')
    
    return {
        'filename': new_name,
        'total_lines': len(merged_rows),
        'original_lines': total_original_lines
    }
