package xaero.pixelmon;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import java.nio.file.StandardOpenOption;
import org.apache.logging.log4j.LogManager;

/** Small private config; never overwrites Xaero's user profiles. Restart to reload. */
public final class MapOptions {
    private static final Properties OPTIONS = read();
    private MapOptions() {}
    public static boolean alwaysShowSprites() { return Boolean.parseBoolean(OPTIONS.getProperty("alwaysShowSprites", "true")); }
    public static double spriteScale() {
        try { double value=Double.parseDouble(OPTIONS.getProperty("spriteScale","0.5")); return Double.isFinite(value) ? Math.max(0.2,Math.min(2.0,value)) : 0.5; }
        catch(NumberFormatException e) { return 0.5; }
    }
    private static Properties read() {
        Path path = Path.of("config", "xaero-pixelmon.properties");
        try {
            if (!Files.exists(path)) {
                Files.createDirectories(path.getParent());
                Files.writeString(path, "# Pokemon and wormhole icons on both Xaero maps.\n# Global radar/server visibility still applies. Restart after changes.\nalwaysShowSprites=true\n# Relative icon size on both maps: default 0.5 (half native size), range 0.2 - 2.0.\nspriteScale=0.5\n", StandardCharsets.UTF_8);
            }
            Properties p = new Properties();
            try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) { p.load(reader); }
            if(!p.containsKey("spriteScale")) Files.writeString(path,"\n# Relative Pokemon/wormhole icon size; restart after changes.\nspriteScale=0.5\n",StandardCharsets.UTF_8,StandardOpenOption.APPEND);
            return p;
        } catch (IOException ex) {
            LogManager.getLogger("XaeroPixelmon").warn("Could not read sprite options; defaults will be used", ex);
            return new Properties();
        }
    }
}
