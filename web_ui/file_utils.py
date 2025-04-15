import re
import json

def normalize_comment_text(text):
    """
    Normalize comment text by removing newline characters.
    (We do not strip leading/trailing spaces to preserve column alignment.)
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
      - Remove any trailing "*/" from the last line.
      - For each line, remove a leading "*" (with an optional following space) if present.
    Returns a list of cleaned lines.
    """
    cleaned = []
    for line in block_lines:
        line = re.sub(r'^\s*/\*', '', line)       # Remove starting /* if present.
        line = re.sub(r'\*/\s*$', '', line)         # Remove ending */ if present.
        line = re.sub(r'^\s*\*\s?', '', line)        # Remove leading * (and an optional space) if present.
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
    
    Returns:
        A dictionary with keys:
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
    Given an original line and a marker (e.g. "#" or "//" or "/*"),
    search for the marker in the line and return the 1-indexed column number where it occurs.
    If not found, return 1.
    """
    pos = original_line.find(marker)
    return pos + 1 if pos != -1 else 1

def process_comments(file_content, comments_data, lang="Python"):
    """
    Process the comments for a file.
    
    Args:
        file_content: Full file content as a string (including newlines).
        comments_data: A dict containing:
            - "metadata": {...}
            - "single_line_comment": list of { "line_number": int, "comment": str }
            - "cont_single_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
            - "multi_line_comment": list of { "start_line": int, "end_line": int, "comment": str }
        lang: "Python" or "Java". For Python, you may choose to skip multi-line comments.
    
    For each comment, this function computes and attaches:
          "computed_start_line", "computed_start_column",
          "computed_end_line", "computed_end_column"
    For single-line comments, it overrides the computed_start_column by searching the original line
    for the appropriate marker.
    
    Returns:
        The updated comments_data dict with computed range fields for each comment.
    """
    file_lines = file_content.splitlines()
    updated_comments = {}

    # Determine marker for single-line comments.
    if lang.lower() == "python":
        single_marker = "#"
    elif lang.lower() == "java":
        single_marker = "//"
    else:
        single_marker = "#"

    # Process single-line comments.
    updated_comments["single_line_comment"] = []
    for cmt in comments_data.get("single_line_comment", []):
        line_number = cmt.get("line_number")
        if not line_number or line_number < 1 or line_number > len(file_lines):
            continue
        original_line = file_lines[line_number - 1]
        block_lines = [original_line]
        range_info = find_comment_range_in_block(cmt["comment"], block_lines, line_offset=line_number - 1)
        # For single-line, override computed_start_column by searching the full original line.
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
        updated_comments["cont_single_line_comment"].append(cmt)
    
    # Process multi-line comments.
    updated_comments["multi_line_comment"] = []
    for cmt in comments_data.get("multi_line_comment", []):
        start_line = cmt.get("start_line")
        end_line = cmt.get("end_line")
        if not start_line or not end_line or start_line < 1 or end_line > len(file_lines):
            continue
        block_lines = file_lines[start_line - 1:end_line]
        # For Java multi-line comments, use "/*" as marker.
        if lang.lower() == "java":
            multi_marker = "/*"
            block_lines = clean_multiline_block(block_lines)
        else:
            multi_marker = "#"
        range_info = find_comment_range_in_block(cmt["comment"], block_lines, line_offset=start_line - 1)
        if range_info:
            first_line = file_lines[start_line - 1]
            marker_pos = get_marker_position(first_line, multi_marker)
            range_info["computed_start_column"] = marker_pos
            cmt.update(range_info)
        else:
            cmt.update({
                "computed_start_line": start_line,
                "computed_start_column": get_marker_position(file_lines[start_line - 1], multi_marker),
                "computed_end_line": end_line,
                "computed_end_column": len(file_lines[end_line - 1])
            })
        updated_comments["multi_line_comment"].append(cmt)
    
    if "metadata" in comments_data:
        updated_comments["metadata"] = comments_data["metadata"]
    
    return updated_comments



# For testing purposes: 
if __name__ == "__main__":
    file_content ="/*\n * Licensed to the Apache Software Foundation (ASF) under one\n * or more contributor license agreements. See the NOTICE file\n * distributed with this work for additional information\n * regarding copyright ownership. The ASF licenses this file\n * to you under the Apache License, Version 2.0 (the\n * \"License\"); you may not use this file except in compliance\n * with the License. You may obtain a copy of the License at\n *\n *   http://www.apache.org/licenses/LICENSE-2.0\n *\n * Unless required by applicable law or agreed to in writing,\n * software distributed under the License is distributed on an\n * \"AS IS\" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY\n * KIND, either express or implied. See the License for the\n * specific language governing permissions and limitations\n * under the License.\n */\n\npackage org.apache.thrift.test;\n\nimport java.nio.ByteBuffer;\nimport java.util.LinkedList;\n\nimport thrift.test.OneOfEachBeans;\n\npublic class JavaBeansTest {\n  public static void main(String[] args) throws Exception {\n    // Test isSet methods\n    OneOfEachBeans ooe = new OneOfEachBeans();\n\n    // Nothing should be set\n    if (ooe.is_set_a_bite())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_base64())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_byte_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_double_precision())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_i16_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_i64_list())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_boolean_field())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer16())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer32())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_integer64())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n    if (ooe.is_set_some_characters())\n      throw new RuntimeException(\"isSet method error: unset field returned as set!\");\n\n    for (int i = 1; i < 12; i++){\n      if (ooe.isSet(ooe.fieldForId(i)))\n        throw new RuntimeException(\"isSet method error: unset field \" + i + \" returned as set!\");\n    }\n\n    // Everything is set\n    ooe.set_a_bite((byte) 1);\n    ooe.set_base64(ByteBuffer.wrap(\"bytes\".getBytes()));\n    ooe.set_byte_list(new LinkedList<Byte>());\n    ooe.set_double_precision(1);\n    ooe.set_i16_list(new LinkedList<Short>());\n    ooe.set_i64_list(new LinkedList<Long>());\n    ooe.set_boolean_field(true);\n    ooe.set_integer16((short) 1);\n    ooe.set_integer32(1);\n    ooe.set_integer64(1);\n    ooe.set_some_characters(\"string\");\n\n    if (!ooe.is_set_a_bite())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_base64())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_byte_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_double_precision())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_i16_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_i64_list())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_boolean_field())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer16())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer32())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_integer64())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n    if (!ooe.is_set_some_characters())\n      throw new RuntimeException(\"isSet method error: set field returned as unset!\");\n\n    for (int i = 1; i < 12; i++){\n      if (!ooe.isSet(ooe.fieldForId(i)))\n        throw new RuntimeException(\"isSet method error: set field \" + i + \" returned as unset!\");\n    }\n\n    // Should throw exception when field doesn't exist\n    boolean exceptionThrown = false;\n    try{\n      if (ooe.isSet(ooe.fieldForId(100)));\n    } catch (IllegalArgumentException e){\n      exceptionThrown = true;\n    }\n    if (!exceptionThrown)\n      throw new RuntimeException(\"isSet method error: non-existent field provided as agument but no exception thrown!\");\n  }\n}\n"
    # Example comments data (simulate what you might have)
    comments_data={
            "metadata": {
                "filename": "tmpuefnfrl9_file2.java",
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
