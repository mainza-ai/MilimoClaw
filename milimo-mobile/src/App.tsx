// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Milimo Mobile - Main Application
 *
 * React Native app for War Room companion on mobile devices.
 */

import React from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import PendingListScreen from './screens/PendingList';
import ActionDetailScreen from './screens/ActionDetail';
import SettingsScreen from './screens/Settings';

export type RootStackParamList = {
  PendingList: undefined;
  ActionDetail: { actionId: string };
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar barStyle="dark-content" />
        <Stack.Navigator
          initialRouteName="PendingList"
          screenOptions={{
            headerStyle: {
              backgroundColor: '#1a1a2e',
            },
            headerTintColor: '#fff',
            headerTitleStyle: {
              fontWeight: '600',
            },
          }}
        >
          <Stack.Screen
            name="PendingList"
            component={PendingListScreen}
            options={{
              title: 'War Room',
              headerLargeTitle: true,
            }}
          />
          <Stack.Screen
            name="ActionDetail"
            component={ActionDetailScreen}
            options={{
              title: 'Action Details',
              headerBackTitle: 'Back',
            }}
          />
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{
              title: 'Settings',
              presentation: 'modal',
            }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

export default App;
