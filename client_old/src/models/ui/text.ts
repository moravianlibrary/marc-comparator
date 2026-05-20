export type CountUiText = (values: { count: number }) => string;
export type StaticUiText = string;
export type UiText = StaticUiText | CountUiText;
