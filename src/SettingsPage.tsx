// SettingsPage.tsx
import { VFC } from 'react';
import { lazy } from 'react';
//import WithSuspense from 'decky-frontend-lib'
import MyForm from './ServerDetails';
import AnotherForm from './SoundSettings';
import assForm from './ass';
import { ServerAPI, SidebarNavigation } from "decky-frontend-lib";


interface SettingsPageProps {
  serverAPI: ServerAPI;
}

//const MyForm = lazy(() => import("./ServerDetails"));
//const AnotherForm = lazy(() => import("./AnotherForm"));

const SettingsPage: VFC<SettingsPageProps> = ({ serverAPI }) => {
  const pages = [
    {
      title: 'Server Settings',
      content: <MyForm serverAPI={serverAPI} />,
      route: '/deckmumble/settings/form1',
    },
    {
      title: 'Sound Settings',
      content: <AnotherForm serverAPI={serverAPI} />,
      route: '/deckmumble/settings/form2',
    },
  ];
  return (<SidebarNavigation pages={pages}/>);
};

export default SettingsPage