import { type ReactElement } from "react";
import {
    Split,
    SplitItem,
    Form,
    FormSelect,
    FormSelectOption,
} from "@patternfly/react-core";
import type { AuthorityLink } from "../../models/api/responses/authority_link";
import { useTranslation } from "react-i18next";

interface AuthorityBaseSelectProps {
    authorityLinks: AuthorityLink[];
    base: string | null;
    onSubmit: (base: string) => void;
}

const AuthorityBaseSelect = ({
    authorityLinks,
    base,
    onSubmit,
}: AuthorityBaseSelectProps): ReactElement | null => {
    const { t } = useTranslation();

    return (
        <Form isHorizontal onSubmit={(e) => e.preventDefault()}>
            <Split hasGutter>
                <SplitItem>
                    <FormSelect
                        id="authority-base-select"
                        value={base || ""}
                        onChange={(_, value) => value && onSubmit(value)}
                    >
                        {base === null ? (
                            <FormSelectOption
                                key="placeholder"
                                label={t(
                                    "records:details.authority-links.select-base-placeholder"
                                )}
                                isPlaceholder
                            />
                        ) : null}
                        {authorityLinks
                            ?.filter(
                                (item, index, arr) =>
                                    arr.findIndex(
                                        (x) => x.base === item.base
                                    ) === index
                            )
                            .map((link, i) => (
                                <FormSelectOption
                                    key={i}
                                    value={link.base}
                                    label={link.base}
                                />
                            ))}
                    </FormSelect>
                </SplitItem>
            </Split>
        </Form>
    );
};

export default AuthorityBaseSelect;
