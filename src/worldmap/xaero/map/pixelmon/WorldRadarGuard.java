package xaero.map.pixelmon;

import net.minecraft.client.Minecraft;
import net.minecraft.entity.Entity;
import xaero.common.XaeroMinimapSession;
import xaero.map.element.render.ElementRenderInfo;

/** Do not project live entities from another dimension onto the selected map. */
public final class WorldRadarGuard {
    private WorldRadarGuard() {}
    public static boolean canRender(Object element, ElementRenderInfo info) {
        if (!(element instanceof Entity)) return true;
        Entity entity = (Entity)element;
        Minecraft mc = Minecraft.func_71410_x();
        return info != null && mc.field_71441_e != null && entity.field_70170_p == mc.field_71441_e
            && info.mapDimension != null && info.mapDimension.equals(entity.field_70170_p.func_234923_W_());
    }
    public static boolean sessionReady() {
        Minecraft mc = Minecraft.func_71410_x();
        return mc.field_71441_e != null && mc.field_71439_g != null && XaeroMinimapSession.getCurrentSession() != null;
    }
}
