// Ace token names vary by language. Map the roles exposed by each mode.
ace.define('ace/theme/sunset', ['require', 'exports', 'module'], function (require, exports) {
  exports.isDark = true;
  exports.cssClass = 'ace-sunset';
  exports.cssText = `
.ace-sunset {
  --muted: color-mix(in srgb, var(--sunset-foreground) 68%, var(--sunset-background));
  background: var(--sunset-background);
  color: var(--sunset-foreground);
}
.ace-sunset .ace_gutter { background: var(--sunset-background); color: var(--muted); }
.ace-sunset .ace_gutter-active-line,
.ace-sunset .ace_marker-layer .ace_active-line { background: var(--sunset-black); }
.ace-sunset .ace_marker-layer .ace_selection { background: var(--sunset-selectionBackground); }
.ace-sunset .ace_marker-layer .ace_bracket,
.ace-sunset .ace_marker-layer .ace_selected-word { border: 1px solid var(--muted); }
.ace-sunset .ace_cursor { color: var(--sunset-cursor); }
.ace-sunset .ace_invisible { color: var(--sunset-brightBlack); }
.ace-sunset .ace_comment { color: var(--muted); font-style: italic; }
.ace-sunset .ace_keyword, .ace-sunset .ace_storage,
.ace-sunset .ace_constant, .ace-sunset .ace_support.ace_function { color: var(--sunset-magenta); }
.ace-sunset .ace_keyword.ace_control, .ace-sunset .ace_storage.ace_type.ace_builtin,
.ace-sunset .ace_support.ace_type { color: var(--sunset-brightMagenta); }
.ace-sunset .ace_entity.ace_name.ace_function, .ace-sunset .ace_meta.ace_tag,
.ace-sunset .ace_entity.ace_name.ace_tag { color: var(--sunset-blue); }
.ace-sunset .ace_entity.ace_name.ace_type, .ace-sunset .ace_entity.ace_name.ace_class,
.ace-sunset .ace_support.ace_class, .ace-sunset .ace_storage.ace_type { color: var(--sunset-yellow); }
.ace-sunset .ace_string { color: var(--sunset-green); }
.ace-sunset .ace_variable.ace_parameter, .ace-sunset .ace_variable.ace_language { color: var(--sunset-red); }
.ace-sunset .ace_variable.ace_property, .ace-sunset .ace_entity.ace_other.ace_attribute-name { color: var(--sunset-cyan); }
.ace-sunset .ace_punctuation, .ace-sunset .ace_paren { color: var(--muted); }
.ace-sunset .ace_keyword.ace_operator, .ace-sunset .ace_constant.ace_character { color: var(--sunset-brightCyan); }
.ace-sunset .ace_string.ace_regexp, .ace-sunset .ace_constant.ace_character.ace_escape,
.ace-sunset .ace_meta.ace_preprocessor { color: var(--sunset-brightYellow); }
.ace-sunset .ace_invalid { color: var(--sunset-red); background: var(--sunset-black); }
`;
});
