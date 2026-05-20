import React, { useRef, useEffect } from "react";
import * as d3 from "d3";

interface ArcSegment {
    start: number;
    end: number;
    color: string;
}

interface SemiCircularGaugeProps {
    value: number;
    segments?: ArcSegment[];
    width?: number | string;
    height?: number | string;
}

const SemiCircularGauge: React.FC<SemiCircularGaugeProps> = ({
    value,
    segments = [
        { start: 0, end: 70, color: "#F89B78" },
        { start: 70, end: 90, color: "#FFCC17" },
        { start: 90, end: 100, color: "#63993D" },
    ],
    width = 300,
    height = 180,
}) => {
    const svgRef = useRef<SVGSVGElement | null>(null);

    useEffect(() => {
        const svgEl = svgRef.current;
        if (!svgEl) return;

        const svg = d3.select(svgEl);
        svg.selectAll("*").remove();

        const textMargin = 35;
        const w = svgEl.clientWidth;
        const h = svgEl.clientHeight;
        const radius = Math.min(w, h * 2) / 2 - textMargin / 2;

        // percent → angle (-90° to 90°)
        const scale = d3
            .scaleLinear()
            .domain([0, 100])
            .range([-Math.PI / 2, Math.PI / 2]);

        // Shift upward so the gauge fits nicely
        const g = svg
            .append("g")
            .attr("transform", `translate(${w / 2}, ${h - textMargin})`);

        const arc = d3
            .arc()
            .innerRadius(radius - 25)
            .outerRadius(radius);

        // Draw segments
        g.selectAll("path")
            .data(segments)
            .enter()
            .append("path")
            .attr(
                "d",
                (d) =>
                    arc({
                        startAngle: scale(d.start === 0 ? -1 : d.start),
                        endAngle: scale(d.end === 100 ? 101 : d.end),
                    })!
            )
            .attr("fill", (d) => d.color);

        // ----- Draw tapered needle -----
        const angle = scale(Math.max(0, Math.min(100, value))) - Math.PI / 2;

        const needleLength = radius;
        const needleWidthBase = 15; // wide at base
        const needleWidthTip = 3; // narrow at tip
        const needleMargin = 5;

        const baseLeftX = Math.cos(angle + Math.PI / 2) * (needleWidthBase / 2);
        const baseLeftY = Math.sin(angle + Math.PI / 2) * (needleWidthBase / 2);

        const baseRightX =
            Math.cos(angle - Math.PI / 2) * (needleWidthBase / 2);
        const baseRightY =
            Math.sin(angle - Math.PI / 2) * (needleWidthBase / 2);

        const tipCenterX =
            Math.cos(angle) * (needleLength - needleWidthTip - needleMargin);
        const tipCenterY =
            Math.sin(angle) * (needleLength - needleWidthTip - needleMargin);

        const path = d3.path();
        path.moveTo(baseLeftX, baseLeftY);
        path.lineTo(baseRightX, baseRightY);
        // Draw semicircle at the tip
        path.arc(
            tipCenterX,
            tipCenterY,
            needleWidthTip,
            angle - Math.PI / 2,
            angle + Math.PI / 2
        );
        path.closePath();

        g.append("path").attr("d", path.toString()).attr("fill", "#333");

        // ----- Text below gauge -----
        svg.append("text")
            .attr("x", w / 2)
            .attr("y", h - 5)
            .attr("text-anchor", "middle")
            .attr("font-size", "22px")
            .attr("font-weight", "600")
            .text(`${value.toFixed(1)}%`);
    }, [value, width, height]);

    return <svg ref={svgRef} width={width} height={height} />;
};

export default SemiCircularGauge;
