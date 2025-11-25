import {
    Brand,
    Masthead,
    MastheadBrand,
    MastheadContent,
    MastheadLogo,
    MastheadMain,
    MastheadToggle,
    PageToggleButton,
} from "@patternfly/react-core";
import type { ReactElement } from "react";
import MainPageMastheadToolbar from "./MastheadToolbar";

const MainPageMasthead = (): ReactElement => {
    return (
        <Masthead>
            <MastheadMain>
                <MastheadToggle>
                    <PageToggleButton
                        isHamburgerButton
                        aria-label="Global navigation"
                    />
                </MastheadToggle>
                <MastheadBrand>
                    <MastheadLogo>
                        <Brand
                            src="/marcomparator-logo-dark-text-transparent.png"
                            alt="Marc Comparator"
                        />
                    </MastheadLogo>
                </MastheadBrand>
            </MastheadMain>
            <MastheadContent>
                <MainPageMastheadToolbar />
            </MastheadContent>
        </Masthead>
    );
};

export default MainPageMasthead;
