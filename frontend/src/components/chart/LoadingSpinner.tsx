import React from 'react';
import { Spin } from 'antd';

interface LoadingSpinnerProps {
    isLoading: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ isLoading }) => {
    if (!isLoading) return null;

    return (
        <div style={{
            position: 'absolute',
            left: '50%',
            bottom: '20px',
            transform: 'translateX(-50%)',
            background: 'rgba(255, 255, 255, 0.9)',
            padding: '8px 16px',
            borderRadius: '4px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            zIndex: 1000,
        }}>
            <Spin size="small" /> Loading historical data...
        </div>
    );
}; 