import { Space, Typography } from "antd";

interface ITableDatetimeProps {
  time: string;
}
export default ({ time }: ITableDatetimeProps) => {
  const localeString = time.split("T")[0];
  const localeTime = time.split("T")[1].split(".")[0];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <Typography.Text>{localeString}</Typography.Text>
      <Typography.Text type="secondary">{localeTime}</Typography.Text>
    </div>
  );
};
