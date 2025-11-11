import { useRef, useEffect, useState } from "react";
import * as d3 from "d3";

interface RangeSliderProps {
    min: number;
    max: number;
    from: number;
    to: number;
    step?: number;
    histogramData?: { x: number; y: number }[];
    onChange: (from: number, to: number) => void;
}

const RangeSlider = ({
    min,
    max,
    from,
    to,
    step = 1,
    histogramData,
    onChange,
}: RangeSliderProps) => {
    const svgRef = useRef<SVGSVGElement | null>(null);
    const [currentFrom, setCurrentFrom] = useState(from);
    const [currentTo, setCurrentTo] = useState(to);

    const height = 120;
    const margin = { top: 10, right: 20, bottom: 20, left: 20 };
    const handleRadius = 8;

    useEffect(() => {
        if (!svgRef.current) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        const width = svgRef.current.clientWidth;

        const xScale = d3
            .scaleLinear()
            .domain([min, max])
            .range([margin.left, width - margin.right]);

        // Histogram bars
        if (histogramData?.length) {
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

        // X Axis
        const xAxis = d3.axisBottom(xScale).ticks(5);
        const xAxisGroup = svg
            .append("g")
            .attr("transform", `translate(0, ${height - margin.bottom})`)
            .call(xAxis);

        xAxisGroup.selectAll("text").style("font-size", "16px");

        // Selection rectangle
        const selection = svg
            .append("rect")
            .attr("x", xScale(currentFrom))
            .attr("y", margin.top)
            .attr("width", xScale(currentTo) - xScale(currentFrom))
            .attr("height", height - margin.top - margin.bottom)
            .attr("fill", "#3182bd")
            .attr("fill-opacity", 0.3);

        const dragHandle = (isFrom: boolean) =>
            d3
                .drag<SVGCircleElement, unknown>()
                .on(
                    "drag",
                    (
                        event: d3.D3DragEvent<
                            SVGCircleElement,
                            unknown,
                            unknown
                        >
                    ) => {
                        const newX = Math.max(
                            margin.left,
                            Math.min(width - margin.right, event.x)
                        );
                        const value =
                            Math.round(xScale.invert(newX) / step) * step;

                        if (isFrom) {
                            if (value >= currentTo) return;
                            setCurrentFrom(value);
                        } else {
                            if (value <= currentFrom) return;
                            setCurrentTo(value);
                        }
                    }
                )
                .on(
                    "end",
                    (
                        event: d3.D3DragEvent<
                            SVGCircleElement,
                            unknown,
                            unknown
                        >
                    ) => {
                        // Trigger onChange once drag is complete
                        const newX = Math.max(
                            margin.left,
                            Math.min(width - margin.right, event.x)
                        );
                        const value =
                            Math.round(xScale.invert(newX) / step) * step;

                        if (isFrom) {
                            onChange(value, currentTo);
                        } else {
                            onChange(currentFrom, value);
                        }
                    }
                );

        // Handles
        svg.append("circle")
            .attr("cx", xScale(currentFrom))
            .attr("cy", (height - margin.bottom + margin.top) / 2)
            .attr("r", handleRadius)
            .attr("fill", "#3182bd")
            .call(dragHandle(true));

        svg.append("circle")
            .attr("cx", xScale(currentTo))
            .attr("cy", (height - margin.bottom + margin.top) / 2)
            .attr("r", handleRadius)
            .attr("fill", "#3182bd")
            .call(dragHandle(false));

        // Update selection on state change
        selection
            .attr("x", xScale(currentFrom))
            .attr("width", xScale(currentTo) - xScale(currentFrom));
    }, [currentFrom, currentTo, histogramData, min, max, step, onChange]);

    useEffect(() => {
        setCurrentFrom(from);
        setCurrentTo(to);
    }, [from, to]);

    return <svg ref={svgRef} width="100%" height={height} />;
};

export default RangeSlider;
