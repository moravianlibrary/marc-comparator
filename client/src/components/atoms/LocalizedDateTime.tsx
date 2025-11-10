interface LocalizedDateTimeProps {
    date: Date;
}

const LocalizedDateTime = ({ date }: LocalizedDateTimeProps) => {
    const locale = "sk-SK";

    const formatted = date.toLocaleString(locale, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });

    return (
        <span
            style={{
                fontFamily: "monospace",
                whiteSpace: "nowrap",
                fontSize: "0.8rem",
            }}
        >
            {formatted}
        </span>
    );
};

export default LocalizedDateTime;
