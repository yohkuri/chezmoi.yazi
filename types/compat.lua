---@meta _

-- Missing declarations in the pinned types.yazi revision, verified against
-- yazi-rs/yazi v26.9.1: yazi-plugin/preset/components/linemode.lua,
-- yazi-binding/src/process/child.rs.
---@alias ChezmoiLinemodeChild fun(row: Linemode): string|ui.Line

---@class Linemode
---@field _file fs__File
---@field new fun(self: self, file: fs__File): Linemode
---@field redraw fun(self: self): ui.Line
---@field children_add fun(self: self, callback: ChezmoiLinemodeChild, order: number): integer
---@field children_remove fun(self: self, id: integer)
Linemode = Linemode

---@class Child
---@field try_wait fun(self: self): Status?, Error?

-- Plugin-specific configuration, merged by Yazi from flavor and theme.
---@class th
---@field chezmoi? table<string, string|ui.Style>

-- yazi-actor/src/lives/file.rs exposes current-list membership on live files.
---@class fs__File
---@field in_current boolean

-- Yazi v26.9.1 yazi-plugin/src/utils/json.rs.
---@class ya
---@field json_encode fun(value: any): string

-- ui.hide() returns the terminal permit; drop restores Yazi's screen.
---@class Permit
---@field drop fun(self: Permit)
