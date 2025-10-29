export type DynamicUiText = (
    values?: Record<string, string | number>
) => string;
export type StaticUiText = string;
export type UiText = StaticUiText | DynamicUiText;
