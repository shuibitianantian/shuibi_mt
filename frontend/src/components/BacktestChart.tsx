import React from 'react';
import { BacktestResult } from '../types/strategy';
import { Card, Row, Col, Statistic } from 'antd';
import useChart from './chart/hooks/useChart';

interface Props {
    data: BacktestResult;
}

export const BacktestChart: React.FC<Props> = ({ data }) => {
    const { chartContainerRef } = useChart({ data });

    return (
        <div style={{ width: '100%' }}>
            <Row gutter={[8, 8]} style={{ marginBottom: 8 }}>
                <Col span={4}>
                    <Card size="small">
                        <Statistic
                            title="Total Return"
                            value={data.stats['Total Return (%)']}
                            precision={2}
                            suffix="%"
                            valueStyle={{
                                color: data.stats['Total Return (%)'] >= 0 ? '#3f8600' : '#cf1322',
                                fontSize: '14px'
                            }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card size="small">
                        <Statistic
                            title="Annual Return"
                            value={data.stats['Annual Return (%)']}
                            precision={2}
                            suffix="%"
                            valueStyle={{
                                color: data.stats['Annual Return (%)'] >= 0 ? '#3f8600' : '#cf1322',
                                fontSize: '14px'
                            }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card size="small">
                        <Statistic
                            title="Max Drawdown"
                            value={data.stats['Max Drawdown (%)']}
                            precision={2}
                            suffix="%"
                            valueStyle={{
                                color: '#cf1322',
                                fontSize: '14px'
                            }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card size="small">
                        <Statistic
                            title="Sharpe Ratio"
                            value={data.stats['Sharpe Ratio']}
                            precision={2}
                            valueStyle={{
                                color: data.stats['Sharpe Ratio'] >= 1 ? '#3f8600' : '#cf1322',
                                fontSize: '14px'
                            }}
                        />
                    </Card>
                </Col>
                <Col span={4}>
                    <Card size="small">
                        <Statistic
                            title="Win Rate"
                            value={data.stats['Win Rate (%)']}
                            precision={2}
                            suffix="%"
                            valueStyle={{
                                color: data.stats['Win Rate (%)'] >= 50 ? '#3f8600' : '#cf1322',
                                fontSize: '14px'
                            }}
                        />
                    </Card>
                </Col>
            </Row>
            <div ref={chartContainerRef} style={{ width: '100%' }} />
        </div>
    );
}; 