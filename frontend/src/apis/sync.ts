import { message } from "antd";

export const downloadLatestData = async () => {
  try {
    const response = await fetch("http://localhost:8000/api/download-latest", {
      method: "POST",
    });
    const { taskId } = await response.json();
    message.loading("Downloading data...", 500000);

    // 定期检查下载状态
    const checkStatus = async () => {
      const statusResponse = await fetch(
        `http://localhost:8000/api/download-status/${taskId}`
      );
      const status = await statusResponse.json();

      if (status.state === "completed") {
        message.destroy();
        message.success("Data download completed");
        return;
      } else if (status.state === "failed") {
        message.error(`Download failed: ${status.error}`);
        return;
      }

      // 继续检查
      setTimeout(checkStatus, 2000);
    };

    checkStatus();
  } catch (error) {
    message.error("Failed to start data download");
  }
};
