import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

class LeonardoService extends ChangeNotifier {
  Process? _process;

  // Stato UI
  bool isRunning = false;
  bool isGeneratingReport = false;
  String currentContext = "";
  bool isWaitingForAdvice = false;

  // Gestione Consigli Iniziali
  String? initialAdvice;
  bool isAdviceAcknowledged = false;

  // Dati in tempo reale
  String activeWindow = "Waiting...";
  int totalTime = 0;
  int switches = 0;
  List<dynamic> topApps = [];

  // Report finale
  String? finalReport;
  Map<String, dynamic>? finalStats;

  // Feedback Leonardo
  String emotion = "neutral";
  String leoComment = "I am observing your work.";
  int focusScore = 100;

  // 1. Rileva automaticamente l'eseguibile Python
  String get pythonExec => Platform.isWindows ? 'python' : 'python3';

  // 2. Calcola il percorso backend in modo relativo
  String get backendPath =>
      p.join(Directory.current.parent.path, 'leonardo_backend', 'trackers');

  final String scriptName = 'trackers.py';

  Future<void> startSession(String context) async {
    currentContext = context;
    isRunning = true;
    finalReport = null;
    finalStats = null;

    // Reset advice per la nuova sessione
    initialAdvice = null;
    isAdviceAcknowledged = false;
    isWaitingForAdvice = true;

    focusScore = 100;

    notifyListeners();

    debugPrint("🚀 FLUTTER: Avvio Sessione...");
    debugPrint("📂 Directory di lavoro: $backendPath");
    debugPrint("🐍 Eseguibile: $pythonExec");
    debugPrint("🎯 Contesto: $context");

    try {
      _process = await Process.start(
        pythonExec,
        ['-u', scriptName, context],
        workingDirectory: backendPath,
        runInShell: true,
      );

      debugPrint("✅ Processo avviato (PID: ${_process!.pid})");

      _process!.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) {
            _parsePythonOutput(line);
          });

      _process!.stderr.transform(utf8.decoder).listen((data) {
        if (data.trim().isNotEmpty) {
          if (data.contains("[DEBUG]") ||
              data.contains("🛑") ||
              data.contains("===")) {
            debugPrint("PYTHON LOG: ${data.trim()}\n");
          } else {
            debugPrint("❌ PYTHON ERROR: $data");
          }
        }
      });
    } catch (e) {
      debugPrint("❌ ERRORE LANCIO FLUTTER: $e");
      isRunning = false;
      notifyListeners();
    }
  }

  void _parsePythonOutput(String line) {
    try {
      if (!line.trim().startsWith('{')) return;

      final data = jsonDecode(line);
      final type = data['type'] as String?;

      if (type == null) return;

      switch (type) {
        // ============================================
        // CONSIGLI INIZIALI
        // ============================================
        case 'initial_advice':
          debugPrint("📜 Advice received from Python");
          initialAdvice = data['content'];
          isWaitingForAdvice = false;
          isAdviceAcknowledged = false;
          notifyListeners();
          break;

        // ============================================
        // UPDATE REAL-TIME (ogni secondo)
        // ============================================
        case 'update':
          activeWindow = data['active_window'] ?? "Idle";
          totalTime = data['total_time'] ?? 0;
          switches = data['switches'] ?? 0;
          topApps = data['top_apps'] ?? [];
          notifyListeners();
          break;

        // ============================================
        // COMMENTO LEONARDO (ogni 30s)
        // ============================================
        case 'leo_comment':
          if (data.containsKey('content')) {
            leoComment = data['content'];
          }

          if (data.containsKey('emotion')) {
            emotion = data['emotion'].toString().toLowerCase();
          }

          // ⭐ Aggiorna focus score
          if (data.containsKey('focus_score')) {
            focusScore = data['focus_score'] ?? 100;
          }

          notifyListeners();
          break;

        // ============================================
        // STATUS GENERICO (es. "generating report...")
        // ============================================
        case 'status':
          isGeneratingReport = true;
          leoComment = data['message'] ?? "Generating report...";
          notifyListeners();
          break;

        // ============================================
        // REPORT FINALE ⭐ CON STATS COMPLETO
        // ============================================
        case 'report':
          debugPrint("📊 Report ricevuto da Python");

          finalReport = data['content'];

          final stats = data['stats'] as Map<String, dynamic>?;

          // ⭐ Estrai metriche finali per Quick Stats
          finalStats = {
            'final_score': data['final_score'] ?? focusScore,
            'grade': data['grade'] ?? _calculateGrade(focusScore),
            'total_iterations': data['total_iterations'] ?? 0,
            'duration_seconds': stats?['duration_seconds'] ?? totalTime,
            'total_switches': stats?['total_switches'] ?? switches,
            'top_apps': stats?['top_apps'] ?? [],
            'total_distraction_time': stats?['total_distraction_time'] ?? 0,
            'pause_count': stats?['pause_count'] ?? 0,
          };

          debugPrint("✅ Stats estratte: $finalStats");

          isGeneratingReport = false;
          isRunning = false;

          notifyListeners();
          _process?.kill();
          break;

        default:
          debugPrint("⚠️ Unknown message type: $type");
      }
    } catch (e) {
      debugPrint("⚠️ Errore parsing JSON: $e");
      debugPrint("   Line: $line");
    }
  }

  // ============================================
  // HELPER: Calcola grade da score
  // ============================================
  String _calculateGrade(int score) {
    if (score >= 90) return "A+";
    if (score >= 85) return "A";
    if (score >= 80) return "A-";
    if (score >= 75) return "B+";
    if (score >= 70) return "B";
    if (score >= 65) return "B-";
    if (score >= 60) return "C+";
    if (score >= 50) return "C";
    return "D";
  }

  // ============================================
  // ACKNOWLEDGE ADVICE (sblocca Python)
  // ============================================
  void acknowledgeAdvice() {
    debugPrint("✅ User acknowledged advice");
    _process?.stdin.writeln('START');
    isAdviceAcknowledged = true;
    notifyListeners();
  }

  // ============================================
  // STOP SESSION
  // ============================================
  Future<void> stopSession() async {
    debugPrint("🛑 Invio segnale di stop a Python...");
    _process?.stdin.writeln('STOP');

    // Aspetta un po' per permettere a Python di generare il report
    await Future.delayed(const Duration(milliseconds: 500));
  }

  // ============================================
  // RESET (nuova sessione)
  // ============================================
  void reset() {
    debugPrint("🔄 Resetting application state...");

    // Report e stats
    finalReport = null;
    finalStats = null;

    // Stato sessione
    isRunning = false;
    isGeneratingReport = false;

    // Dati real-time
    activeWindow = "Waiting...";
    totalTime = 0;
    switches = 0;
    topApps = [];

    // Context e consigli
    currentContext = "";
    initialAdvice = null;
    isAdviceAcknowledged = false;
    isWaitingForAdvice = false;

    // Leonardo feedback
    emotion = "neutral";
    leoComment = "Observing your craft...";
    focusScore = 100;

    notifyListeners();
  }

  // ============================================
  // DISPOSE
  // ============================================
  @override
  void dispose() {
    _process?.kill();
    super.dispose();
  }
}
