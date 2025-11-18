import type { ReactElement } from "react";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import type { EsHit } from "../../models/api/responses/es";
import {
    Split,
    SplitItem,
    Form,
    FormSelect,
    FormSelectOption,
} from "@patternfly/react-core";

interface AuthorityBaseSelectProps {
    record: EsHit<CatalogRecord>;
    base: string | null;
    onSubmit: (base: string) => void;
}

const AuthorityBaseSelect = ({
    record,
    base,
    onSubmit,
}: AuthorityBaseSelectProps): ReactElement => {
    console.log("AuthorityBaseSelect render with base:", base);
    return (
        <Form isHorizontal onSubmit={(e) => e.preventDefault()}>
            <Split hasGutter>
                <SplitItem>
                    <FormSelect
                        id="authority-base-select"
                        value={base || ""}
                        onChange={(_, value) => onSubmit(value)}
                        placeholder="Select authority base"
                    >
                        <FormSelectOption
                            key="empty"
                            value=""
                            label="Select authority base"
                            isPlaceholder
                        />
                        {record._source.authority_links
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
