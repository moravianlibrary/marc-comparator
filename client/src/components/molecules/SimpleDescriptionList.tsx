import {
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
} from "@patternfly/react-core";

interface SimpleDescriptionListGroup {
    term: React.ReactNode;
    description: React.ReactNode;
}

interface SimpleDescriptionListProps {
    groups: SimpleDescriptionListGroup[];
    isHorizontal?: boolean;
}

export const SimpleDescriptionList = ({
    groups,
    isHorizontal,
}: SimpleDescriptionListProps): React.ReactElement => (
    <DescriptionList isHorizontal={isHorizontal}>
        {groups.map(({ term, description }, index) => (
            <DescriptionListGroup key={index}>
                <DescriptionListTerm>{term}</DescriptionListTerm>
                <DescriptionListDescription>
                    {description}
                </DescriptionListDescription>
            </DescriptionListGroup>
        ))}
    </DescriptionList>
);

export default SimpleDescriptionList;
