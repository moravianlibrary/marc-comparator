import { Label, LabelGroup } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import type { AuthorityLink } from "../../../models/api/responses/authority_link";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";

const AuthorityLinkLabel = ({
    recordId,
    authorityLink: { base },
}: {
    recordId: string;
    authorityLink: AuthorityLink;
}): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=authority_records&authorityLinks.base=${base}`,
                )
            }
        >
            {base}
        </Label>
    );
};

const AuthorityLinkLabelGroup = ({
    hit: {
        _id,
        _source: { authority_links },
    },
}: {
    hit: EsHit<CatalogRecord>;
}) => {
    if (!authority_links || authority_links.length === 0) return null;

    return (
        <LabelGroup>
            {authority_links
                .sort((a, b) => a.base.localeCompare(b.base))
                .map((authorityLink, index) => (
                    <AuthorityLinkLabel
                        key={index}
                        authorityLink={authorityLink}
                        recordId={_id}
                    />
                ))}
        </LabelGroup>
    );
};

export { AuthorityLinkLabel, AuthorityLinkLabelGroup };
