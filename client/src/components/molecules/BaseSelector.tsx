import { ReactElement } from "react";
import SingleSelect from "../molecules/SingleSelect";

interface BaseSelectorProps {
    availableBases: string[];
    selected: string | null;
    onChange: (base: string | null) => void;
    placeholder: string;
}

const BaseSelector = ({
    availableBases,
    selected,
    onChange,
    placeholder,
}: BaseSelectorProps): ReactElement => {
    return (
        <SingleSelect
            placeholder={placeholder}
            options={availableBases.map((base) => ({
                label: base,
                value: base,
            }))}
            selected={selected ? { label: selected, value: selected } : null}
            onChange={(option) =>
                onChange(option ? (option.value as string) : null)
            }
            isDisabled={availableBases.length === 0}
        />
    );
};

export default BaseSelector;
