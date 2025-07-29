import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'screens/home_screen.dart';
import 'screens/processing_screen.dart';
import 'screens/results_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(
    const ProviderScope(
      child: GpthGuiApp(),
    ),
  );
}

class GpthGuiApp extends StatelessWidget {
  const GpthGuiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Google Photos Takeout Helper',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}

final _router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      name: 'home',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/processing',
      name: 'processing',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return ProcessingScreen(
          config: extra?['config'],
        );
      },
    ),
    GoRoute(
      path: '/results',
      name: 'results',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return ResultsScreen(
          result: extra?['result'],
        );
      },
    ),
  ],
);