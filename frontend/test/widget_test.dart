import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:leonardoapp/main.dart';
import 'package:leonardoapp/process_service.dart';

void main() {
  testWidgets('l\'app si avvia e mostra la schermata di setup', (tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => LeonardoService(),
        child: const LeoFocusApp(),
      ),
    );

    // Niente pumpAndSettle: HomeScreen ha un AnimationController in repeat().
    await tester.pump();

    expect(find.text('Salve, curious mind!'), findsOneWidget);
  });
}
