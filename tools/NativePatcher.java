import java.nio.file.*;
import java.util.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

/** Source-controlled edits to exact, hash-locked Xaero class files. */
public final class NativePatcher implements Opcodes {
    private static final String BRIDGE = "xaero/pixelmon/PixelmonSprites";
    static MethodNode method(ClassNode c, String name, String descriptor) {
        return c.methods.stream().filter(m -> m.name.equals(name) && m.desc.equals(descriptor)).findFirst()
            .orElseThrow(() -> new IllegalStateException("Unrecognised upstream API: " + c.name + "." + name + descriptor));
    }
    static InsnList nullableReturn(String owner, String method, String descriptor, int argument, String frameType) {
        InsnList p = new InsnList(); LabelNode fallback = new LabelNode();
        p.add(new VarInsnNode(ALOAD, argument));
        p.add(new MethodInsnNode(INVOKESTATIC, owner, method, descriptor, false));
        p.add(new InsnNode(DUP)); p.add(new JumpInsnNode(IFNULL, fallback)); p.add(new InsnNode(ARETURN));
        p.add(fallback); p.add(new FrameNode(F_SAME1, 0, null, 1, new Object[]{frameType})); p.add(new InsnNode(POP));
        return p;
    }
    static void guard(MethodNode m, InsnList check) {
        LabelNode proceed = new LabelNode();
        check.add(new JumpInsnNode(IFNE, proceed)); check.add(new InsnNode(ICONST_0)); check.add(new InsnNode(IRETURN));
        check.add(proceed); check.add(new FrameNode(F_SAME, 0, null, 0, null)); m.instructions.insert(check);
    }
    public static void main(String[] args) throws Exception {
        Path in = Path.of(args[0]), out = Path.of(args[1]);
        ClassNode c = new ClassNode(); new ClassReader(Files.readAllBytes(in)).accept(c, 0);
        switch(c.name) {
            case "xaero/hud/minimap/radar/icon/cache/id/variant/RadarIconVariantHandler":
                method(c, "getEntityVariant", "(Lxaero/hud/minimap/radar/icon/definition/RadarIconDefinition;Lnet/minecraft/entity/Entity;Lnet/minecraft/client/renderer/entity/EntityRenderer;)Ljava/lang/Object;")
                    .instructions.insert(nullableReturn(BRIDGE, "variant", "(Lnet/minecraft/entity/Entity;)Ljava/lang/Object;", 2, "java/lang/Object"));
                break;
            case "xaero/hud/minimap/radar/icon/definition/RadarIconDefinitionManager":
                method(c, "get", "(Lnet/minecraft/util/ResourceLocation;)Lxaero/hud/minimap/radar/icon/definition/RadarIconDefinition;")
                    .instructions.insert(nullableReturn(BRIDGE, "definition", "(Lnet/minecraft/util/ResourceLocation;)Lxaero/hud/minimap/radar/icon/definition/RadarIconDefinition;", 1, "xaero/hud/minimap/radar/icon/definition/RadarIconDefinition"));
                break;
            case "xaero/hud/minimap/radar/render/element/RadarRenderProvider": {
                MethodNode m = method(c, "setupContextForEntity", "(Lnet/minecraft/entity/Entity;Lxaero/hud/minimap/radar/render/element/RadarRenderContext;)V");
                int edits = 0;
                for (AbstractInsnNode n : m.instructions.toArray()) if (n.getOpcode() == RETURN) {
                    InsnList p = new InsnList(); p.add(new VarInsnNode(ALOAD, 1)); p.add(new VarInsnNode(ALOAD, 2));
                    p.add(new MethodInsnNode(INVOKESTATIC, BRIDGE, "configureContext", "(Lnet/minecraft/entity/Entity;Lxaero/hud/minimap/radar/render/element/RadarRenderContext;)V", false));
                    m.instructions.insertBefore(n, p); edits++;
                }
                if (edits == 0) throw new IllegalStateException("No radar provider exit");
                break;
            }
            case "xaero/common/settings/ModSettings": {
                if (c.fields.stream().anyMatch(f -> f.name.equals("ENCHANT_COLORS"))) throw new IllegalStateException("Palette already exists");
                c.fields.add(new FieldNode(ACC_PUBLIC | ACC_STATIC | ACC_FINAL, "ENCHANT_COLORS", "[Ljava/lang/String;", null, null));
                // Legacy integrations use this palette to select the constructor's vanilla index.
                InsnList p = new InsnList(); p.add(new IntInsnNode(BIPUSH, 16)); p.add(new TypeInsnNode(ANEWARRAY, "java/lang/String"));
                String[] colors = {"black","dark_blue","dark_green","dark_aqua","dark_red","dark_purple","gold","gray","dark_gray","blue","green","aqua","red","light_purple","yellow","white"};
                for (int i=0;i<colors.length;i++) { p.add(new InsnNode(DUP)); p.add(new IntInsnNode(BIPUSH,i)); p.add(new LdcInsnNode(colors[i])); p.add(new InsnNode(AASTORE)); }
                p.add(new FieldInsnNode(PUTSTATIC,c.name,"ENCHANT_COLORS","[Ljava/lang/String;"));
                method(c,"<clinit>","()V").instructions.insert(p);
                break;
            }
            case "xaero/map/mods/minimap/element/MinimapElementRendererWrapper": {
                String owner = "xaero/map/pixelmon/WorldRadarGuard";
                MethodNode m = method(c, "renderElement", "(Ljava/lang/Object;ZDFDDLxaero/map/element/render/ElementRenderInfo;Lcom/mojang/blaze3d/matrix/MatrixStack;Lnet/minecraft/client/renderer/IRenderTypeBuffer$Impl;Lxaero/map/graphics/renderer/multitexture/MultiTextureRenderTypeRendererProvider;)Z");
                InsnList p = new InsnList(); p.add(new VarInsnNode(ALOAD,1)); p.add(new VarInsnNode(ALOAD,10));
                p.add(new MethodInsnNode(INVOKESTATIC,owner,"canRender","(Ljava/lang/Object;Lxaero/map/element/render/ElementRenderInfo;)Z",false)); guard(m,p);
                MethodNode should = method(c, "shouldRender", "(IZ)Z"); p = new InsnList();
                p.add(new MethodInsnNode(INVOKESTATIC,owner,"sessionReady","()Z",false)); guard(should,p);
                break;
            }
            default: throw new IllegalArgumentException("Not an approved patch target: " + c.name);
        }
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS); c.accept(writer);
        Files.createDirectories(out.getParent()); Files.write(out, writer.toByteArray());
        System.out.println(c.name);
    }
}
