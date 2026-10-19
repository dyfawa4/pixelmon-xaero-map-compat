package xaero.pixelmon;

import java.io.IOException;
import net.minecraft.client.Minecraft;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.fml.LogicalSide;
import org.apache.logging.log4j.LogManager;
import xaero.common.minimap.waypoints.Waypoint;
import xaero.hud.minimap.BuiltInHudModules;
import xaero.hud.minimap.module.MinimapSession;
import xaero.hud.minimap.waypoint.WaypointColor;
import xaero.hud.minimap.waypoint.set.WaypointSet;
import xaero.hud.minimap.world.MinimapWorld;

/** The edited compass's old callback is replaced inside our Xaero component. */
public final class CompassCompat {
    private CompassCompat() {}
    public static boolean isLocalTick(TickEvent.PlayerTickEvent event) {
        return event.side == LogicalSide.CLIENT && event.phase == TickEvent.Phase.END
            && event.player == Minecraft.func_71410_x().field_71439_g;
    }
    public static void addPoint(int x, int z, PlayerEntity player, String name) {
        Minecraft mc = Minecraft.func_71410_x();
        if (player == null || player != mc.field_71439_g || mc.field_71441_e == null || name == null || name.isBlank()) return;
        MinimapSession session = BuiltInHudModules.MINIMAP.getCurrentSession();
        if (session == null) return;
        MinimapWorld world = session.getWorldManager().getCurrentWorld();
        // The world manager can lag one frame behind a portal transition.
        if (world == null || !mc.field_71441_e.func_234923_W_().equals(world.getDimId())) return;
        WaypointSet set = world.getCurrentWaypointSet();
        if (set == null) return;
        for (Waypoint existing : set.getWaypoints()) {
            if (existing.getX() == x && existing.getZ() == z && name.equals(existing.getName())) return;
        }
        String symbol = new String(Character.toChars(name.codePointAt(0)));
        Waypoint point = new Waypoint(x, (int)Math.floor(player.func_226278_cu_()), z, name, symbol, WaypointColor.GOLD);
        set.add(point);
        try {
            session.getWorldManagerIO().saveWorld(world);
        } catch (IOException ex) {
            LogManager.getLogger("XaeroPixelmon").error("Compass marker added in memory but could not be saved", ex);
        }
    }
}
