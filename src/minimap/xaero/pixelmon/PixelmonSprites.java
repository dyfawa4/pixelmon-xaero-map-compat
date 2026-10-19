package xaero.pixelmon;

import com.pixelmonmod.pixelmon.entities.WormholeEntity;
import com.pixelmonmod.pixelmon.entities.pixelmon.PixelmonEntity;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.entity.Entity;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.fml.ModList;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import xaero.hud.minimap.radar.icon.definition.RadarIconDefinition;
import xaero.hud.minimap.radar.icon.definition.form.RadarIconBasicForms;
import xaero.hud.minimap.radar.icon.definition.form.RadarIconForm;
import xaero.hud.minimap.radar.icon.definition.form.sprite.RadarIconSpriteForm;
import xaero.hud.minimap.radar.icon.definition.form.type.RadarIconFormTypes;
import xaero.hud.minimap.radar.render.element.RadarRenderContext;
import xaero.hud.minimap.radar.category.setting.EntityRadarCategorySettings;

/** Native Xaero radar sprites, using the exact Pixelmon JourneyMap sprite API. */
public final class PixelmonSprites {
    private static final Logger LOG = LogManager.getLogger("XaeroPixelmon");
    private static final AtomicBoolean FAILED = new AtomicBoolean();
    private static final RadarIconDefinition DYNAMIC = new DynamicDefinition();
    private static final ResourceLocation WORMHOLE = new ResourceLocation("pixelmon", "textures/gui/overlay/externalmoves/wormhole.png");
    private PixelmonSprites() {}

    public static boolean isPixelmonEntity(Entity entity) {
        return ModList.get().isLoaded("pixelmon") && (entity instanceof PixelmonEntity || entity instanceof WormholeEntity);
    }

    /** String keys share native Xaero caches by sprite, not by transient entity IDs. */
    public static Object variant(Entity entity) {
        if (!ModList.get().isLoaded("pixelmon")) return null;
        try {
            if (entity instanceof PixelmonEntity) {
                ResourceLocation sprite = ((PixelmonEntity)entity).getSprite();
                return sprite == null ? "default" : sprite.toString();
            }
            if (entity instanceof WormholeEntity) return WORMHOLE.toString();
        } catch (RuntimeException | LinkageError ex) {
            if (FAILED.compareAndSet(false, true)) LOG.error("Unable to resolve Pixelmon sprite; native radar fallback will be used", ex);
        }
        return null;
    }

    public static RadarIconDefinition definition(ResourceLocation type) {
        if (type == null || !ModList.get().isLoaded("pixelmon")) return null;
        String key = type.toString();
        return key.equals("pixelmon:pixelmon") || key.equals("pixelmon:ultra_wormhole") ? DYNAMIC : null;
    }

    /** Global radar visibility/server restrictions still run before this hook. */
    public static void configureContext(Entity entity, RadarRenderContext context) {
        // Native setupContextForEntity only resets the icon flag. Reset from the
        // category for EVERY entity, so adjacent sprites never shrink cumulatively
        // and a following vanilla mob never inherits the Pokemon scale.
        if (context.radarList != null) context.iconScale = (Double)context.radarList.getEffective(EntityRadarCategorySettings.ICON_SCALE);
        if (isPixelmonEntity(entity)) {
            if (MapOptions.alwaysShowSprites()) context.icon = true;
            context.iconScale *= MapOptions.spriteScale();
        }
    }

    private static final class DynamicDefinition extends RadarIconDefinition {
        @Override public RadarIconForm getVariantForm(String key) {
            if (key == null || key.equals("default")) return RadarIconBasicForms.DOT;
            ResourceLocation sprite = ResourceLocation.func_208304_a(key);
            if (sprite == null) return RadarIconBasicForms.DOT;
            // Point at the mod's live resource. No copied/stale species icon catalogue.
            return new RadarIconSpriteForm(RadarIconFormTypes.OUTLINED_SPRITE, sprite);
        }
    }
}
