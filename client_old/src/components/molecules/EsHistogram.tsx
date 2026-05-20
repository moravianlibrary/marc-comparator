import {
    useEffect,
    useRef,
    useState,
    type Dispatch,
    type ReactElement,
} from "react";
import type {
    EsHistogramFilterConfig,
    EsState,
    EsStateAction,
} from "../../store/es/domain";
import type { CollectionData } from "../../store/collection/domain";
import { selectHistogramBuckets } from "../../store/es/selectors";
import {
    Button,
    Card,
    CardBody,
    CardTitle,
    Divider,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import * as d3 from "d3";

const EsHistogram = <T,>({
    field,
    data,
    state,
    dispatch,
    title,
}: {
    field: string;
    data?: CollectionData<T>;
    state: EsState;
    dispatch: Dispatch<EsStateAction>;

    title?: React.ReactNode;
}): ReactElement | null => {
    const config = state.config.filters?.[field] as
        | EsHistogramFilterConfig
        | undefined;
    if (!config) return null;

    const coef = config.coef ?? 1;

    const histogramState = state.hist?.[field];

    const buckets = selectHistogramBuckets(field, state, data);
    if (buckets.length === 0) return null;

    const min = (config.min ?? Math.min(...buckets.map((b) => b.key))) * coef;
    const max = (config.max ?? Math.max(...buckets.map((b) => b.key))) * coef;

    const gte = histogramState?.gte ? histogramState.gte * coef : min;
    const lte = histogramState?.lte ? histogramState.lte * coef : max;
    const isActive =
        histogramState?.gte !== undefined || histogramState?.lte !== undefined;

    // Convert histogram buckets to midpoint data for RangeSlider
    const valueLookup = buckets.reduce<Record<number, number>>((acc, b) => {
        acc[b.key * coef] = b.doc_count;
        return acc;
    }, {});
    const interval = config.interval * coef;
    const histogramData = Array.from(
        { length: Math.floor((max - min) / interval) + 1 },
        (_, i) => {
            const x = min + i * interval;
            return { x, y: valueLookup[x] ?? 0 };
        }
    );

    return (
        <Card isPlain key={field}>
            <CardTitle>
                <Split hasGutter>
                    <SplitItem>{title || field}</SplitItem>
                    {isActive && (
                        <SplitItem>
                            <Button
                                variant="link"
                                style={{ padding: 0 }}
                                onClick={() =>
                                    dispatch({
                                        type: "setHistogramRange",
                                        field,
                                        gte: undefined,
                                        lte: undefined,
                                    })
                                }
                            >
                                Reset
                            </Button>
                        </SplitItem>
                    )}
                </Split>
            </CardTitle>
            <Divider />
            <CardBody>
                <RangeSlider
                    min={min}
                    max={max}
                    gte={gte}
                    lte={lte}
                    histogramData={histogramData}
                    onChange={(gte, lte) =>
                        dispatch({
                            type: "setHistogramRange",
                            field,
                            gte: gte / coef,
                            lte: lte / coef,
                        })
                    }
                />
            </CardBody>
        </Card>
    );
};

interface RangeSliderProps {
    min: number;
    max: number;
    gte: number;
    lte: number;
    step?: number;
    histogramData: { x: number; y: number }[];
    onChange: (gte: number, lte: number) => void;
}
const RangeSlider = ({
    min,
    max,
    gte,
    lte,
    step = 1,
    histogramData,
    onChange,
}: RangeSliderProps) => {
    const svgRef = useRef<SVGSVGElement | null>(null);

    const [currentGte, setCurrentGte] = useState(gte);
    const [currentLte, setCurrentLte] = useState(lte);

    const height = 120;
    const margin = { top: 10, right: 20, bottom: 20, left: 20 };
    const handleRadius = 8;

    useEffect(() => {
        if (!svgRef.current) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        const width = svgRef.current.clientWidth;

        const isActive = currentGte !== min || currentLte !== max;

        const halfBarWidth =
            (width - margin.left - margin.right) / histogramData.length / 2;

        const xScale = d3
            .scaleLinear()
            .domain([min, max])
            .range([margin.left, width - margin.right]);

        // Histogram bars
        if (histogramData.length) {
            const yScale = d3
                .scaleLinear()
                .domain([0, d3.max(histogramData, (d) => d.y)!])
                .range([height - margin.bottom, margin.top]);

            svg.append("g")
                .selectAll("rect")
                .data(histogramData)
                .join("rect")
                .attr(
                    "x",
                    (d) =>
                        xScale(d.x) -
                        (width - margin.left - margin.right) /
                            histogramData.length /
                            2
                )
                .attr("y", (d) => yScale(d.y))
                .attr(
                    "width",
                    (width - margin.left - margin.right) /
                        histogramData.length -
                        1
                )
                .attr("height", (d) => height - margin.bottom - yScale(d.y))
                .attr("fill", "#c6dbef");
        }

        // Axis
        const xAxis = d3.axisBottom(xScale).ticks(5);
        svg.append("g")
            .attr("transform", `translate(0, ${height - margin.bottom})`)
            .call(xAxis);

        const selection = svg
            .append("rect")
            .attr("x", xScale(currentGte))
            .attr("y", margin.top)
            .attr("width", xScale(currentLte) - xScale(currentGte))
            .attr("height", height - margin.top - margin.bottom)
            .attr("fill", isActive ? "#3182bd" : "#AAAAAA")
            .attr("fill-opacity", 0.3);

        const dragHandle = (isLeft: boolean) =>
            d3
                .drag<SVGCircleElement, unknown>()
                .on("drag", (event) => {
                    const newX = Math.max(
                        margin.left,
                        Math.min(width - margin.right, event.x)
                    );
                    const value = Math.round(xScale.invert(newX) / step) * step;

                    if (isLeft) {
                        // left cannot exceed right
                        if (value >= currentLte) return;
                        setCurrentGte(value);
                    } else {
                        // right cannot go below left
                        if (value <= currentGte) return;
                        setCurrentLte(value);
                    }
                })
                .on("end", (event) => {
                    const newX = Math.max(
                        margin.left,
                        Math.min(width - margin.right, event.x)
                    );
                    const value = Math.round(xScale.invert(newX) / step) * step;

                    if (isLeft) {
                        onChange(value, currentLte);
                    } else {
                        onChange(currentGte, value);
                    }
                });

        svg.append("circle")
            .attr("cx", xScale(currentGte) - halfBarWidth)
            .attr("cy", (height - margin.bottom + margin.top) / 2)
            .attr("r", handleRadius)
            .attr("fill", "#3182bd")
            .call(dragHandle(true));

        svg.append("circle")
            .attr("cx", xScale(currentLte) + halfBarWidth)
            .attr("cy", (height - margin.bottom + margin.top) / 2)
            .attr("r", handleRadius)
            .attr("fill", "#3182bd")
            .call(dragHandle(false));

        // Update selection
        selection
            .attr("x", xScale(currentGte) - halfBarWidth)
            .attr(
                "width",
                xScale(currentLte) - xScale(currentGte) + 2 * halfBarWidth
            );
    }, [currentLte, currentGte, histogramData, min, max, step, onChange]);

    useEffect(() => {
        setCurrentGte(gte);
        setCurrentLte(lte);
    }, [gte, lte]);

    return <svg ref={svgRef} width="100%" height={height} />;
};

export default EsHistogram;
