package com.tyranor.next.impacto;

import android.app.Activity;
import android.app.ActivityManager;
import android.content.ComponentName;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.util.Log;
import android.widget.Toast;

import java.io.File;
import java.io.IOException;
import java.util.List;

/**
 * Exported entry point for the Tyranor Next app. It validates the request, makes sure this APK may read the game
 * folder, prepares the per-game data root and then starts {@link TyranorImpactoActivity}, which is not exported.
 *
 * <p>The checks live here and not in the game activity because an {@code Activity} subclass must call
 * {@code super.onCreate}, and that would already start the engine.
 */
public final class ImpactoLaunchActivity extends Activity {
    private static final String TAG = "ImpactoLaunch";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            launch(getIntent());
        } catch (RuntimeException e) {
            // Never let a hostile or malformed request take down this process: it also hosts the running game.
            Log.w(TAG, "Launch request failed", e);
        } finally {
            finish();
        }
    }

    /** The engine runs in the {@code :game} process (see the manifest); true while that process is alive. */
    private boolean isGameProcessRunning() {
        try {
            ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
            List<ActivityManager.RunningAppProcessInfo> processes =
                    manager == null ? null : manager.getRunningAppProcesses();
            if (processes == null) {
                return false;
            }
            String gameProcess = getPackageName() + ":game";
            for (ActivityManager.RunningAppProcessInfo info : processes) {
                if (gameProcess.equals(info.processName)) {
                    return true;
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "Could not list running processes", e);
        }
        return false;
    }

    private void launch(Intent incoming) {
        if (incoming == null || !ImpactoRequest.ACTION_RUN.equals(incoming.getAction())) {
            return;
        }
        ImpactoRequest request = ImpactoIntents.read(incoming);
        if (request == null) {
            Log.w(TAG, "Rejected launch request");
            Toast.makeText(this, R.string.request_rejected, Toast.LENGTH_LONG).show();
            return;
        }

        // The game folder lives on shared storage; an app needs all-files access to read it through a path.
        if (!Environment.isExternalStorageManager()) {
            Toast.makeText(this, R.string.need_all_files_access, Toast.LENGTH_LONG).show();
            Intent settings = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    .setData(Uri.parse("package:" + getPackageName()))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(settings);
            return;
        }
        if (!new File(request.gameDir).isDirectory()) {
            Toast.makeText(this, R.string.game_dir_missing, Toast.LENGTH_LONG).show();
            return;
        }

        // The data root lives in internal storage: shared and app-specific external storage are FUSE-backed on
        // Android and refuse symbolic links (verified on a device), while internal storage allows them.
        File filesDir = getFilesDir();
        File root;
        try {
            root = request.prepareDataRoot(filesDir);
        } catch (IOException | RuntimeException e) {
            Log.e(TAG, "Could not prepare the data root", e);
            Toast.makeText(this, R.string.storage_unavailable, Toast.LENGTH_LONG).show();
            return;
        }
        // Read the game folder through the link the engine will use, so an unreadable folder is reported here.
        String[] entries = new File(root, "gamedata/" + request.profile).list();
        if (entries == null) {
            Log.e(TAG, "The game folder is not readable through the data-root link");
            Toast.makeText(this, R.string.game_dir_unreadable, Toast.LENGTH_LONG).show();
            return;
        }
        Log.i(TAG, "Game folder readable through the link: " + entries.length + " entries");

        // Apply the user settings from Tyranor Next to this game's engine config before the engine reads it.
        // A failure here must not stop the game from starting: the engine then simply uses its own values.
        // While the game process is already running the engine owns the file (it rewrites it on its own schedule),
        // so a second launch leaves it alone.
        if (isGameProcessRunning()) {
            Log.i(TAG, "The game is already running; not touching its user config");
        } else {
            try {
                ImpactoUserConfig.apply(new File(root, ImpactoUserConfig.FILE_NAME),
                        ImpactoIntents.readSettings(incoming), request.profile);
            } catch (IOException | RuntimeException e) {
                Log.w(TAG, "Could not apply the user settings", e);
            }
        }

        Intent game = new Intent()
                .setComponent(new ComponentName(this, TyranorImpactoActivity.class))
                .putExtra(ImpactoRequest.EXTRA_GAME_DIR, request.gameDir)
                .putExtra(ImpactoRequest.EXTRA_PROFILE, request.profile)
                .putExtra(ImpactoRequest.EXTRA_GAME_KEY, request.gameKey)
                .putExtra(ImpactoRequest.EXTRA_TITLE, request.title)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Boolean touchControls = ImpactoIntents.readSettings(incoming).touchControls;
        if (touchControls != null) {
            game.putExtra(ImpactoSettings.EXTRA_TOUCH_CONTROLS, touchControls.booleanValue());
        }
        startActivity(game);
    }
}
