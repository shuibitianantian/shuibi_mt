import { Layout, message } from 'antd';
import './App.css';
import { BacktestChart } from './components/BacktestChart';

const { Header, Content } = Layout;

export default () => {
  const [_, contextHolder] = message.useMessage();


  return (
    <Layout className="app-layout">
      {contextHolder}
      <Header className="header">
        <h1>Shuibi MT</h1>
      </Header>
      <Content className="content">
        <BacktestChart />
      </Content>
    </Layout>
  );
}; 