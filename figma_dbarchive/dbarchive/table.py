import json
import sqlite3
from .utils import px, o, deg

def create_table(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS nodes (
        file_id TEXT,
        node_id TEXT,
        parent_id TEXT,
        type TEXT,
        name TEXT,
        data TEXT,
        depth INTEGER,
        children TEXT,
        n_children INTEGER,
        x REAL,
        x_abs REAL,
        y REAL,
        y_abs REAL,
        width REAL,
        height REAL,
        rotation REAL,
        opacity REAL,
        color TEXT,
        canvas_id TEXT,
        text TEXT,
        font_family TEXT,
        font_weight TEXT,
        font_size REAL,
        text_align TEXT,
        border_width REAL,
        border_color TEXT,
        border_radius REAL,
        box_shadow_offset_x REAL,
        box_shadow_offset_y REAL,
        box_shadow_blur REAL,
        box_shadow_spread REAL,
        margin_top REAL,
        margin_right REAL,
        margin_left REAL,
        margin_bottom REAL,
        padding_top REAL,
        padding_left REAL,
        padding_right REAL,
        padding_bottom REAL,
        PRIMARY KEY (file_id, node_id)
    )''')

def insert_node(
        conn: sqlite3.Connection,
        **kwargs
    ):

    # Unpack the kwargs dictionary using tuple assignment
    (
        file_id, node_id, parent_id, _type, name,
        data, depth, children, n_children,
        x, x_abs, y, y_abs, width, height, rotation,
        opacity, color,
        canvas_id,
        text, font_family, font_weight, font_size, text_align,
        border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        margin_top, margin_right, margin_left, margin_bottom,
        padding_top, padding_left, padding_right, padding_bottom
    ) = (
        kwargs['file_id'], kwargs['node_id'], kwargs.get('parent_id'), kwargs['type'], kwargs['name'],
        kwargs.get('data'), kwargs.get('depth'), kwargs.get('children'), kwargs.get('n_children'),
        kwargs['x'], kwargs['x_abs'], kwargs['y'], kwargs['y_abs'], kwargs['width'], kwargs['height'], kwargs.get('rotation'),
        kwargs.get('opacity'), kwargs.get('color'),
        kwargs.get('canvas_id'),
        kwargs.get('text'), kwargs.get('font_family'), kwargs.get('font_weight'), kwargs.get('font_size'), kwargs.get('text_align'),
        kwargs.get('border_width'), kwargs.get('border_color'), kwargs.get('border_radius'),
        kwargs.get('box_shadow_offset_x'), kwargs.get('box_shadow_offset_y'), kwargs.get('box_shadow_blur'), kwargs.get('box_shadow_spread'),
        kwargs.get('margin_top'), kwargs.get('margin_right'), kwargs.get('margin_left'), kwargs.get('margin_bottom'),
        kwargs.get('padding_top'), kwargs.get('padding_left'), kwargs.get('padding_right'), kwargs.get('padding_bottom')
    )

    cursor = conn.cursor()

    if data is not None and type(data) is not str:
        data = json.dumps(data, indent=0, separators=(',', ':'))

    cursor.execute('''INSERT OR IGNORE INTO nodes (
        file_id, node_id, parent_id, type, name, data, depth, children, n_children,
        x, x_abs, y, y_abs, width, height,
        rotation, opacity, color, canvas_id, text,
        font_family, font_weight, font_size, text_align,
        border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        margin_top, margin_right, margin_left, margin_bottom,
        padding_top, padding_left, padding_right, padding_bottom
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        file_id, node_id, parent_id, _type, name, data, depth, children, n_children,
        px(x), px(x_abs), px(y), px(y_abs), px(width), px(height),
        deg(rotation), o(opacity), color, canvas_id, text,
        font_family, font_weight, font_size, text_align,
        px(border_width), border_color, px(border_radius),
        px(box_shadow_offset_x), px(box_shadow_offset_y), px(box_shadow_blur), px(box_shadow_spread),
        px(margin_top), px(margin_right), px(margin_left), px(margin_bottom),
        px(padding_top), px(padding_left), px(padding_right), px(padding_bottom)
    ))
    conn.commit()


def get_node(conn: sqlite3.Connection, file_id: str, node_id: str):
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM nodes WHERE file_id = ? AND node_id = ?''', (file_id, node_id))
    return cursor.fetchone()