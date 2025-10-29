export interface ActionItemConfig {
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
}

export interface ActionSectionConfig {
    label: string;
    icon?: React.ReactNode;
    actions: ActionConfig[];
}

export type ActionConfig = ActionItemConfig | ActionSectionConfig;
