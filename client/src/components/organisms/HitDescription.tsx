import {
    DescriptionList,
    DescriptionListGroup,
    DescriptionListTerm,
    DescriptionListDescription,
} from "@patternfly/react-core";
import { type ReactElement, type ReactNode } from "react";
import type { EsHit } from "../../models/api/responses/es";

interface DescriptionTabProps<T> {
    record: EsHit<T>;
    config: {
        key: string;
        label: string;
        render?: (r: EsHit<T>) => ReactNode;
    }[];
    naText?: string;
}

const HitDescription = <T,>({
    record,
    config,
    naText,
}: DescriptionTabProps<T>): ReactElement => (
    <DescriptionList>
        {config
            .filter(({ key }) => {
                const value = record._source[key as keyof T];

                if (value === undefined || value === null) return false;
                if (Array.isArray(value) && value.length === 0) return false;
                if (
                    typeof value === "object" &&
                    !Array.isArray(value) &&
                    Object.keys(value).length === 0
                )
                    return false;

                return true;
            })
            .map(({ key, label, render }) => (
                <DescriptionListGroup key={key}>
                    <DescriptionListTerm>{label}</DescriptionListTerm>
                    <DescriptionListDescription>
                        {render
                            ? render(record)
                            : String(record._source[key as keyof T] || naText)}
                    </DescriptionListDescription>
                </DescriptionListGroup>
            ))}
    </DescriptionList>
);

export default HitDescription;
