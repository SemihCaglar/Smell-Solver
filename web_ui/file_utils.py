import re
import json

CONTEXT_LINES = 15

def normalize_comment_text(text):
    """
    Normalize comment text by removing newline characters.
    (We do not strip leading/trailing spaces so as not to affect column alignment.)
    """
    return text.replace("\n", "")

def build_map_without_newlines(lines):
    """
    Build a normalized string from a list of lines by concatenating them exactly as they appear (without newlines).
    For each character in the normalized string, create a mapping to its (line, column) in the original file.
    
    Args:
        lines: List of strings representing file lines.
    Returns:
        norm_text: The concatenation of all lines (without newlines).
        pos_map: A list of (line, column) for each character in norm_text.
    """
    norm_text = "".join(lines)
    pos_map = []
    for i, line in enumerate(lines, start=1):
        for j, ch in enumerate(line, start=1):
            pos_map.append((i, j))
    return norm_text, pos_map

def clean_multiline_block(block_lines):
    """
    For Java multi-line comments, remove common comment markers:
      - Remove any leading "/*" from the first line.
      - Remove any trailing "*/" (and anything after it) from the last line.
      - For each line, remove a leading "*" (with an optional following space) if present.
    Returns a list of cleaned lines.
    """
    cleaned = []
    for idx, line in enumerate(block_lines):
        if idx == 0:
            line = re.sub(r'^\s*/\*', '', line)  # Remove starting /*
        if idx == len(block_lines) - 1:
            line = re.sub(r'\*/.*$', '', line)    # Remove trailing "*/" and everything after it.
        line = re.sub(r'^\s*\*\s?', '', line)       # Remove leading * (and an optional space) if present.
        cleaned.append(line)
    return cleaned

def find_comment_range_in_block(comment_text, block_lines, line_offset=0):
    """
    Given a block of file lines (list of strings) and a comment text,
    this function:
      1. Concatenates the block lines (ignoring newlines) exactly.
      2. Removes newline characters from the comment text.
      3. Searches for the comment's normalized substring in the normalized block.
      4. Maps the found indices back to original (line, column) positions.
    
    The line_offset is added to computed line numbers so that if block_lines begins at line N,
    the positions are computed relative to the full file.
    
    Returns a dictionary with keys:
            "computed_start_line", "computed_start_column",
            "computed_end_line", "computed_end_column"
        or None if the normalized comment is not found.
    """
    norm_block, pos_map = build_map_without_newlines(block_lines)
    norm_comment = normalize_comment_text(comment_text)
    
    index = norm_block.find(norm_comment)
    if index == -1:
        return None
    
    start_idx = index
    end_idx = index + len(norm_comment) - 1
    
    if start_idx < len(pos_map) and end_idx < len(pos_map):
        mapped_start_line, mapped_start_col = pos_map[start_idx]
        mapped_end_line, mapped_end_col = pos_map[end_idx]
        return {
            "computed_start_line": mapped_start_line + line_offset,
            "computed_start_column": mapped_start_col,
            "computed_end_line": mapped_end_line + line_offset,
            "computed_end_column": mapped_end_col
        }
    else:
        return None

def get_marker_position(original_line, marker):
    """
    Given an original line and a marker (such as "#" for Python, or "//" / "/*" for Java),
    search for the marker in the line and return the 1-indexed column number where it occurs.
    If not found, return 1.
    """
    pos = original_line.find(marker)
    return pos + 1 if pos != -1 else 1

def extract_associated_code(file_content, comment_range, context_lines=CONTEXT_LINES):
    """
    Extract an associated code block around a comment.
    
    Given the full file content (as a string with newlines) and a comment_range dictionary
    (which should include 'computed_start_line' and 'computed_end_line'),
    extract a block of code that extends from (computed_start_line - context_lines)
    to (computed_end_line + context_lines), handling edge cases.
    
    Returns:
        The associated code block as a string.
    """
    lines = file_content.splitlines()
    total_lines = len(lines)
    start_line = max(1, comment_range.get("computed_start_line", 1) - context_lines)
    end_line = min(total_lines, comment_range.get("computed_end_line", total_lines) + context_lines)
    return "\n".join(lines[start_line - 1:end_line])

def process_comments(file_content, comments_data, lang):
    """
    Process the comments for a file.
    
    Args:
        file_content: Full file content as a string (including newlines).
        comments_data: A dict containing:
            - "metadata": { ... }  (should include "lang")
            - "single_line_comment": list of { "line_number": int, "comment": str }
            - "cont_single_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
            - "multi_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
        lang: Optional. If provided, this overrides metadata. Otherwise, metadata["lang"] is used.
    
    For each comment, this function computes and attaches:
          "computed_start_line", "computed_start_column",
          "computed_end_line", "computed_end_column",
          "associated_code" (the context block around the comment).
    
    For single-line comments, computed_start_column is overridden by searching the original line
    for the actual comment marker.
    
    Returns:
        The updated comments_data dict with computed range fields for each comment.
    """
    file_lines = file_content.splitlines()
    updated_comments = {}

    # Set markers based on language.
    if lang.lower() == "python":
        single_marker = "#"
        multi_marker = "#"
    elif lang.lower() == "java":
        single_marker = "//"
        multi_marker = "/*"
    else:
        single_marker = "#"
        multi_marker = "#"
    
    # Process single-line comments.
    updated_comments["single_line_comment"] = []
    for cmt in comments_data.get("single_line_comment", []):
        line_number = cmt.get("line_number")
        if not line_number or line_number < 1 or line_number > len(file_lines):
            continue
        original_line = file_lines[line_number - 1]
        block_lines = [original_line]
        range_info = find_comment_range_in_block(cmt["comment"], block_lines, line_offset=line_number - 1)
        # Override computed_start_column for single-line using the full original line.
        marker_pos = get_marker_position(original_line, single_marker)
        if range_info:
            range_info["computed_start_column"] = marker_pos
            cmt.update(range_info)
        else:
            cmt.update({
                "computed_start_line": line_number,
                "computed_start_column": marker_pos,
                "computed_end_line": line_number,
                "computed_end_column": len(original_line)
            })
        cmt["associated_code"] = extract_associated_code(file_content, cmt)
        updated_comments["single_line_comment"].append(cmt)

    # Process continued single-line comments.
    updated_comments["cont_single_line_comment"] = []
    for cmt in comments_data.get("cont_single_line_comment", []):
        start_line = cmt.get("start_line")
        end_line = cmt.get("end_line")
        if not start_line or not end_line or start_line < 1 or end_line > len(file_lines):
            continue
        block_lines = file_lines[start_line - 1:end_line]
        range_info = find_comment_range_in_block(cmt["comment"], block_lines, line_offset=start_line - 1)
        if range_info:
            first_line = file_lines[start_line - 1]
            marker_pos = get_marker_position(first_line, single_marker)
            range_info["computed_start_column"] = marker_pos
            cmt.update(range_info)
        else:
            cmt.update({
                "computed_start_line": start_line,
                "computed_start_column": get_marker_position(file_lines[start_line - 1], single_marker),
                "computed_end_line": end_line,
                "computed_end_column": len(file_lines[end_line - 1])
            })
        cmt["associated_code"] = extract_associated_code(file_content, cmt)
        updated_comments["cont_single_line_comment"].append(cmt)
    
    # Process multi-line comments.
    if lang.lower() == "python":
        # Skip Python multi-line comments (e.g., docstrings)
        updated_comments["multi_line_comment"] = [] 
    else: 
        updated_comments["multi_line_comment"] = []
        for cmt in comments_data.get("multi_line_comment", []):
            start_line = cmt.get("start_line")
            end_line = cmt.get("end_line")
            if not start_line or not end_line or start_line < 1 or end_line > len(file_lines):
                continue
            # Use original lines for mapping and for marker extraction.
            orig_block_lines = file_lines[start_line - 1:end_line]
            # For text matching only, clean a copy of the block if language is Java.
            if lang.lower() == "java":
                cleaned_block_lines = clean_multiline_block(orig_block_lines)
            else:
                cleaned_block_lines = orig_block_lines
            # Compute the normalized range from the cleaned block.
            range_info = find_comment_range_in_block(cmt["comment"], cleaned_block_lines, line_offset=start_line - 1)
            if range_info:
                # For start, use the original first line (and marker multi_marker).
                marker_pos_start = get_marker_position(orig_block_lines[0], multi_marker)
                range_info["computed_start_column"] = marker_pos_start
                # For end, use the original last line.
                original_last_line = orig_block_lines[-1]
                marker_index = original_last_line.find("*/")
                if marker_index != -1:
                    # The 1-indexed column should be marker_index + length_of("*/").
                    marker_pos_end = marker_index + len("*/")
                else:
                    marker_pos_end = range_info["computed_end_column"]
                range_info["computed_end_column"] = marker_pos_end
                cmt.update(range_info)
            else:
                # Fallback if matching fails: use markers from the original lines.
                original_last_line = orig_block_lines[-1]
                marker_index = original_last_line.find("*/")
                marker_pos_end = marker_index + len("*/") if marker_index != -1 else len(original_last_line)
                cmt.update({
                    "computed_start_line": start_line,
                    "computed_start_column": get_marker_position(orig_block_lines[0], multi_marker),
                    "computed_end_line": end_line,
                    "computed_end_column": marker_pos_end
                })
            cmt["associated_code"] = extract_associated_code(file_content, cmt)
            updated_comments["multi_line_comment"].append(cmt)
    
    if "metadata" in comments_data:
        updated_comments["metadata"] = comments_data["metadata"]
    
    return updated_comments

def add_context_to_comments(comments_data, file_content, lang="Java"):
    """
    Add start and end column numbers and associated code context to each comment.
    Also merge the three comment categories into a single list, with each comment
    including a "category" field indicating its origin.
    
    Args:
        comments_data: A dict containing:
            - "metadata": {...} (optionally including "lang")
            - "single_line_comment": list of { "line_number": int, "comment": str }
            - "cont_single_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
            - "multi_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
        file_content: Full file content as a string (with newlines).
        lang: Optional language indicator (e.g. "Java" or "Python"). If not provided,
              the metadata value will be used (defaulting to "Python" if missing).
              
    Returns:
        A flat list of comments (dicts), each with computed ranges, associated code, 
        and an extra "category" field (one of "single_line", "cont_single_line", or "multi_line").
    """
    # Process comments using our existing utility.
    processed = process_comments(file_content, comments_data, lang)
    
    # Merge all comment types into one list with an added 'category' field.
    merged_comments = []
    category_mapping = {
        "single_line_comment": "single_line",
        "cont_single_line_comment": "cont_single_line",
        "multi_line_comment": "multi_line"
    }
    
    for key, category in category_mapping.items():
        for comment in processed.get(key, []):
            comment["category"] = category
            merged_comments.append(comment)
    
    return merged_comments

def parse_patch_ranges(patch):
    """
    Parse a patch (diff) string to extract hunk ranges from the new file.
    Hunk headers in the patch have the format:
      @@ -old_start,old_len +new_start,new_len @@
    This function extracts the new file's starting line and length and returns a list of (start, end) tuples
    representing the changed lines in the new file.
    
    Returns:
        List of tuples (new_start, new_end).
    """
    ranges = []
    hunk_regex = re.compile(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
    for line in patch.splitlines():
        if line.startswith("@@"):
            match = hunk_regex.search(line)
            if match:
                new_start = int(match.group(1))
                new_length = int(match.group(2)) if match.group(2) else 1
                new_end = new_start + new_length - 1
                ranges.append((new_start, new_end))
    return ranges

def filter_comments_by_diff_intersection(diff_patch, comments, file_content, context_lines=CONTEXT_LINES):
    # TODO check this function. i didnt do any testing on it.
    """
    Given a diff patch string and a list of comment objects (each with computed_start_line and computed_end_line),
    filter out comments that do not intersect with any diff hunk range.
    
    Here, the effective range for each comment is defined as:
         effective_start = max(1, computed_start_line - context_lines)
         effective_end   = min(total_lines, computed_end_line + context_lines)
    
    A comment is retained if there is at least one diff hunk range (from the patch)
    such that the effective comment range overlaps it.
    
    Args:
        diff_patch (str): The diff patch string.
        comments (list): List of comment objects, each containing at least:
                        - computed_start_line (int)
                        - computed_end_line (int)
        file_content (str): Full file content as a string.
        context_lines (int): Number of extra lines to include on either side.
    
    Returns:
        A filtered list (subset of comments) where each comment's effective range intersects at least one diff range.
    """
    # Parse diff patch to get changed line ranges
    diff_ranges = parse_patch_ranges(diff_patch)
    total_lines = len(file_content.splitlines())
    
    filtered_comments = []
    for cmt in comments:
        comp_start = cmt.get("computed_start_line")
        comp_end = cmt.get("computed_end_line")
        # Skip comments that do not have computed values.
        if comp_start is None or comp_end is None:
            continue
        # Extend effective range by context_lines, handling file boundaries.
        effective_start = max(1, comp_start - context_lines)
        effective_end = min(total_lines, comp_end + context_lines)
        
        # Check for intersection with any diff hunk.
        intersects = False
        for diff_start, diff_end in diff_ranges:
            # Intersection exists if the highest start is <= lowest end.
            if max(effective_start, diff_start) <= min(effective_end, diff_end):
                intersects = True
                break
        if intersects:
            filtered_comments.append(cmt)
    return filtered_comments

def replace_comment_block(file_content: str, comment_entry: dict, lang: str = 'java', max_width: int = 80) -> str:
    """
    Replace the comment in file_content as specified by comment_entry, inserting the repair_suggestion
    with appropriate comment markers for the given language, and preserving surrounding code.

    Args:
        file_content: full file text (with newlines).
        comment_entry: dict with keys:
            - computed_start_line, computed_start_column
            - computed_end_line, computed_end_column
            - repair_suggestion (string)
        lang: 'java' or 'python'.
        max_width: maximum line width for wrapping comment text.

    Returns:
        New text for the block of lines [start_line..end_line], including prefix and suffix.
    """
    def wrap_text(text: str, width: int):
        words = text.split()
        if not words:
            return []
        lines, cur = [], words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    # split with newline preserved so suffix keeps its \n
    lines = file_content.splitlines(keepends=True)

    sl, sc = comment_entry["computed_start_line"], comment_entry["computed_start_column"]
    el, ec = comment_entry["computed_end_line"], comment_entry["computed_end_column"]

    prefix = lines[sl - 1][: sc - 1]          # text before comment
    suffix = lines[el - 1][ec:]               # text after comment (may start with \n)

    suggestion = (comment_entry.get("repair_suggestion") or "").strip()

    # if empty suggestion ⇒ delete comment but keep code
    if not suggestion:
        return (prefix + suffix).rstrip("\n")

    # choose markers & wrap width
    if lang.lower() == "java":
        single, mstart, mprefix, mend = "//", "/*", " *", " */"
    else:  # python
        single, mstart, mprefix, mend = "#", "'''", "", "'''"

    wrap_w = max_width - len(single) - 1
    wrapped = wrap_text(suggestion, wrap_w)

    # build comment text
    if len(wrapped) == 1 and len(wrapped[0]) <= wrap_w:
        comment_lines = [f"{single} {wrapped[0]}"]
    else:
        if lang.lower() == "java":
            comment_lines = [f"{mstart} {wrapped[0]}"] + \
                            [f"{mprefix} {ln}" for ln in wrapped[1:]] + [mend]
        else:
            comment_lines = [mstart] + wrapped + [mend]

    # assemble new block
    block_parts = []
    for idx, cl in enumerate(comment_lines):
        if idx == 0:
            text = prefix + cl            # first line keeps prefix
        else:
            text = cl

        if idx == len(comment_lines) - 1:
            # if multi‑line, join will inject '\n' BEFORE this line → avoid double newline
            if len(comment_lines) > 1 and suffix.startswith("\n"):
                text += suffix[1:]
            else:
                text += suffix
        block_parts.append(text)

    return "\n".join(block_parts).rstrip("\n") # remove trailing newline

# For testing purposes: 
if __name__ == "__main__":
    file_content ="/*\n * Licensed to the Apache Software Foundation (ASF) under one\n * or more contributor license agreements. See the NOTICE file\n * distributed with this work for additional information\n * regarding copyright ownership. The ASF licenses this file\n * to you under the Apache License, Version 2.0 (the\n * \"License\"); you may not use this file except in compliance\n * with the License. You may obtain a copy of the License at\n *\n *   http://www.apache.org/licenses/LICENSE-2.0\n *\n * Unless required by applicable law or agreed to in writing,\n * software distributed under the License is distributed on an\n * \"AS IS\" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY\n * KIND, either express or implied. See the License for the\n * specific language governing permissions and limitations\n * under the License.\n */jncdjncdjncdjn\n\npackage org.apache.thrift.test;\n\nimport java.nio.ByteBuffer;\nimport java.util.LinkedList;\n\nimport thrift.test.OneOfEachBeans;\n\npublic class JavaBeansTest {\n  public static void main(String[] args) throws Exception {\n    // Test isSet methods\n    OneOfEachBeans ooe = new OneOfEachBeans();\n\n    // Nothing should be set\n    if (ooe.is_set_a_bite())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_base64())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_byte_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_double_precision())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_i16_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_i64_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_boolean_field())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer16())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer32())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer64())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_some_characters())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n\n    for (int i = 1; i < 12; i++){\n      if (ooe.isSet(ooe.fieldForId(i)))\n        throw new RuntimeException(\"isSet method error: unset field \" + i + \" returned as set!\");\n    }\n\n    // Everything is set\n    ooe.set_a_bite((byte) 1);\n    ooe.set_base64(ByteBuffer.wrap(\"bytes\".getBytes()));\n    ooe.set_byte_list(new LinkedList<Byte>());\n    ooe.set_double_precision(1);\n    ooe.set_i16_list(new LinkedList<Short>());\n    ooe.set_i64_list(new LinkedList<Long>());\n    ooe.set_boolean_field(true);\n    ooe.set_integer16((short) 1);\n    ooe.set_integer32(1);\n    ooe.set_integer64(1);\n    ooe.set_some_characters(\"string\");\n\n    if (!ooe.is_set_a_bite())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_base64())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_byte_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_double_precision())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_i16_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_i64_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_boolean_field())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer16())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer32())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer64())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_some_characters())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n\n    for (int i = 1; i < 12; i++){\n      if (!ooe.isSet(ooe.fieldForId(i)))\n        throw new RuntimeException(\"isSet method error: set field \" + i + \" returned as unset!\");\n    }\n\n    // Should throw exception when field doesn't exist\n    boolean exceptionThrown = false;\n    try{\n      if (ooe.isSet(ooe.fieldForId(100)));\n    } catch (IllegalArgumentException e){\n      exceptionThrown = true;\n    }\n    if (!exceptionThrown)\n      throw new RuntimeException(\"isSet method error: non-existent field provided as agument but no exception thrown!\");\n  }\n}\n"
    # Example comments data (simulate what you might have)
    comments_data={
        "metadata": {
            "filename": "textcomment.java",
            "lang": "Java",
            "total_lines": 112,
            "total_lines_of_comments": 23,
            "blank_lines": 10,
            "sloc": 79
        },
        "single_line_comment": [
            {
                "line_number": 29,
                "comment": "Test isSet methods"
            },
            {
                "line_number": 32,
                "comment": "Nothing should be set"
            },
            {
                "line_number": 61,
                "comment": "Everything is set"
            },
            {
                "line_number": 102,
                "comment": "Should throw exception when field doesn't exist"
            }
        ],
        "cont_single_line_comment": [],
        "multi_line_comment": [
            {
                "start_line": 1,
                "end_line": 18,
                "comment": "Licensed to the Apache Software Foundation (ASF) under one* or more contributor license agreements. See the NOTICE file* distributed with this work for additional information* regarding copyright ownership. The ASF licenses this file* to you under the Apache License, Version 2.0 (the* \"License\"); you may not use this file except in compliance* with the License. You may obtain a copy of the License at**   http://www.apache.org/licenses/LICENSE-2.0** Unless required by applicable law or agreed to in writing,* software distributed under the License is distributed on an* \"AS IS\" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY* KIND, either express or implied. See the License for the* specific language governing permissions and limitations* under the License."
            }
        ]
    }
    
    # Process the comments (for Python, we are skipping multi-line comments)
    processed = process_comments(file_content, comments_data, lang="Java")
    import json
    print(json.dumps(processed, indent=4))
