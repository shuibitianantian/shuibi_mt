import React from "react";
import { Spin } from "antd";

interface LoadingSpinnerProps {
  isLoading: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  isLoading,
}) => {
  if (!isLoading) return null;

  return (
    <Spin
      size="large"
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translateX(-50%) translateY(-50%)",
        padding: "8px 16px",
        borderRadius: "4px",
        zIndex: 1000,
      }}
    />
  );
};
