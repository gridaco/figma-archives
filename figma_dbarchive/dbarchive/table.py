import json
import sqlite3
from .utils import px, o, deg


def create_table(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS nodes (
        file_id TEXT,
        node_id TEXT,
        parent_id TEXT,
        canvas_id TEXT,
        transition_node_id TEXT,
        type TEXT,
        name TEXT,
        visible TEXT,
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
        background_color TEXT,
        background_image TEXT,
        effects TEXT,
        fills TEXT,
        strokes TEXT,
        characters TEXT,
        n_characters INTEGER,
        font_family TEXT,
        font_weight TEXT,
        font_size REAL,
        font_style TEXT,
        text_decoration TEXT,
        text_align TEXT,
        text_align_vertical TEXT,
        text_auto_resize TEXT,
        letter_spacing REAL,
        stroke_linecap TEXT,
        border_alignment TEXT,
        border_width REAL,
        border_color TEXT,
        border_radius REAL,
        box_shadow_offset_x REAL,
        box_shadow_offset_y REAL,
        box_shadow_blur REAL,
        box_shadow_spread REAL,
        padding_top REAL,
        padding_left REAL,
        padding_right REAL,
        padding_bottom REAL,

        constraint_vertical TEXT,
        constraint_horizontal TEXT,

        layout_align TEXT,
        layout_mode TEXT,
        layout_positioning TEXT,
        layout_grow TEXT,
        primary_axis_sizing_mode TEXT,
        counter_axis_sizing_mode TEXT,
        primary_axis_align_items TEXT,
        counter_axis_align_items TEXT,
        gap REAL,
        reverse TEXT,

        fill_geometry TEXT,
        stroke_geometry TEXT,

        transition_duration REAL,
        transition_easing TEXT,
        clips_content TEXT,
        is_mask TEXT,
        export_settings TEXT,
        mix_blend_mode TEXT,
        aspect_ratio REAL,
        PRIMARY KEY (file_id, node_id)
    )''')


def insert_node(
    conn: sqlite3.Connection,
    **kwargs
):

    # Unpack the kwargs dictionary using tuple assignment
    (
        file_id, node_id, parent_id, canvas_id, transition_node_id, _type, name, visible,
        data, depth, children, n_children,
        x, x_abs, y, y_abs, width, height, rotation,
        opacity, color, background_color, background_image, effects, fills, strokes,
        characters, font_family, font_weight, font_size, font_style, text_decoration, text_align, text_align_vertical, text_auto_resize, letter_spacing,
        stroke_linecap, border_alignment, border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        padding_top, padding_left, padding_right, padding_bottom,
        constraint_vertical, constraint_horizontal, layout_align, layout_mode, layout_positioning, layout_grow, primary_axis_sizing_mode, counter_axis_sizing_mode, primary_axis_align_items, counter_axis_align_items, gap, reverse,
        fill_geometry, stroke_geometry,
        transition_duration, transition_easing, clips_content, is_mask, export_settings, mix_blend_mode, aspect_ratio
    ) = (
        kwargs['file_id'], kwargs['node_id'], kwargs.get('parent_id'), kwargs.get('canvas_id'), kwargs.get(
            'transition_node_id'), kwargs['type'], kwargs['name'], kwargs['visible'],
        kwargs.get('data'), kwargs['depth'], kwargs.get(
            'children'), kwargs.get('n_children'),
        kwargs['x'], kwargs['x_abs'], kwargs['y'], kwargs['y_abs'], kwargs['width'], kwargs['height'], kwargs['rotation'],
        kwargs.get('opacity'), kwargs.get('color'), kwargs.get('background_color'), kwargs.get(
            'background_image'), kwargs.get('effects'), kwargs.get('fills'), kwargs.get('strokes'),
        kwargs.get('characters'), kwargs.get('font_family'), kwargs.get('font_weight'), kwargs.get('font_size'), kwargs.get('font_style'), kwargs.get(
            'text_decoration'), kwargs.get('text_align'), kwargs.get('text_align_vertical'), kwargs.get('text_auto_resize'), kwargs.get('letter_spacing'),
        kwargs.get('stroke_linecap'), kwargs.get('border_alignment'), kwargs.get(
            'border_width'), kwargs.get('border_color'), kwargs.get('border_radius'),
        kwargs.get('box_shadow_offset_x'), kwargs.get('box_shadow_offset_y'), kwargs.get(
            'box_shadow_blur'), kwargs.get('box_shadow_spread'),
        kwargs.get('padding_top'), kwargs.get('padding_left'), kwargs.get(
            'padding_right'), kwargs.get('padding_bottom'),
        kwargs.get('constraint_vertical'), kwargs.get('constraint_horizontal'), kwargs.get('layout_align'), kwargs.get('layout_mode'), kwargs.get('layout_positioning'), kwargs.get('layout_grow'), kwargs.get(
            'primary_axis_sizing_mode'), kwargs.get('counter_axis_sizing_mode'), kwargs.get('primary_axis_align_items'), kwargs.get('counter_axis_align_items'), kwargs.get('gap'), kwargs.get('reverse'),
        kwargs.get('fill_geometry'), kwargs.get('stroke_geometry'),
        kwargs.get('transition_duration'), kwargs.get('transition_easing'), kwargs.get('clips_content'), kwargs.get(
            'is_mask'), kwargs.get('export_settings'), kwargs.get('mix_blend_mode'), kwargs.get('aspect_ratio')
    )

    n_characters = len(characters) if characters else None

    cursor = conn.cursor()
    # PUT
    cursor.execute(f'''INSERT OR REPLACE INTO nodes (
        file_id, node_id, parent_id, canvas_id, transition_node_id, type, name, visible, data, depth, children, n_children,
        x, x_abs, y, y_abs, width, height, rotation, opacity, color, background_color, background_image, effects, fills, strokes,
        characters, n_characters, font_family, font_weight, font_size, font_style, text_decoration, text_align, text_align_vertical, text_auto_resize, letter_spacing,
        stroke_linecap, border_alignment, border_width, border_color, border_radius,
        box_shadow_offset_x, box_shadow_offset_y, box_shadow_blur, box_shadow_spread,
        padding_top, padding_left, padding_right, padding_bottom,
        constraint_vertical, constraint_horizontal, layout_align, layout_mode, layout_positioning, layout_grow, primary_axis_sizing_mode, counter_axis_sizing_mode, primary_axis_align_items, counter_axis_align_items, gap, reverse,
        fill_geometry, stroke_geometry,
        transition_duration, transition_easing, clips_content, is_mask, export_settings, mix_blend_mode, aspect_ratio
    ) VALUES ({','.join(['?'] * 71)})''', (
        file_id, node_id, parent_id, canvas_id, transition_node_id, _type, name, visible, data, depth, children, n_children,  # 12
        px(x), px(x_abs), px(y), px(y_abs), px(width), px(height), deg(rotation), o(
            opacity), color, background_color, background_image, effects, fills, strokes,  # 12
        characters, n_characters, font_family, font_weight, px(
            font_size), font_style, text_decoration, text_align, text_align_vertical, text_auto_resize, px(letter_spacing),  # 10
        stroke_linecap, border_alignment, px(
            border_width), border_color, px(border_radius),  # 5
        px(box_shadow_offset_x), px(box_shadow_offset_y), px(
            box_shadow_blur), px(box_shadow_spread),  # 4
        px(padding_top), px(padding_left), px(
            padding_right), px(padding_bottom),
        constraint_vertical, constraint_horizontal, layout_align, layout_mode, layout_positioning, layout_grow, primary_axis_sizing_mode, counter_axis_sizing_mode, primary_axis_align_items, counter_axis_align_items, px(
            gap), reverse,
        fill_geometry, stroke_geometry,
        transition_duration, transition_easing, clips_content, is_mask, export_settings, mix_blend_mode, aspect_ratio
    ))
    conn.commit()


def dumpstr(obj):
    return json.dumps(obj, separators=(',', ':')) if obj is not None and type(obj) is not str else obj


def get_node(conn: sqlite3.Connection, file_id: str, node_id: str):
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT * FROM nodes WHERE file_id = ? AND node_id = ?''', (file_id, node_id))
    return cursor.fetchone()
